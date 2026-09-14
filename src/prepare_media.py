"""Local media -> timestamped Whisper transcript and frame files; no external upload."""
import argparse
import datetime
import importlib.metadata
import json
import math
import subprocess
import time
from pathlib import Path
from course_feedback.pipeline import digest


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--media',required=True); p.add_argument('--out',required=True)
    p.add_argument('--model',default='small',help='faster-whisper model name or local directory')
    p.add_argument('--chunk-seconds',type=int,default=300)
    p.add_argument('--frame-seconds',type=int,default=60)
    p.add_argument('--device',choices=['cpu','cuda'],default='cpu')
    args=p.parse_args()
    out=Path(args.out); out.mkdir(parents=True,exist_ok=True)
    log={'observed_at':datetime.datetime.now().astimezone().isoformat(),'status':'running','chunks':[],
         'frame_status':'not_run','scope':'本地媒体解码、转写及取帧；未做视觉理解'}
    started=time.perf_counter()
    try:
        import av
        import imageio_ffmpeg
        from faster_whisper import WhisperModel
        if args.chunk_seconds<=0 or args.frame_seconds<=0: raise ValueError('时间间隔必须大于0')
        media=Path(args.media).resolve()
        with av.open(str(media)) as container:
            if not container.streams.audio: raise ValueError('媒体没有音轨')
            if container.duration is None: raise ValueError('无法读取媒体时长')
            duration=container.duration/av.time_base
            has_video=bool(container.streams.video)
        if not math.isfinite(duration) or duration<=0: raise ValueError('媒体时长无效')
        fingerprint=digest(media)
        local_weights=Path(args.model)/'model.bin'
        weights_hash=digest(local_weights) if local_weights.is_file() else None
        library_version=importlib.metadata.version('faster-whisper')
        log.update(media_sha256=fingerprint,duration_s=duration,model=args.model,device=args.device,
                   local_model_sha256=weights_hash,faster_whisper_version=library_version)
        ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        model=WhisperModel(args.model,device=args.device,compute_type='int8' if args.device=='cpu' else 'float16')
        all_segments=[]
        for i,start in enumerate(range(0,math.ceil(duration),args.chunk_seconds)):
            end=min(start+args.chunk_seconds,duration)
            # One-second overlapping context; assign segments by midpoint to each core chunk.
            actual_start=max(0,start-1); actual_end=min(duration,end+1)
            cache=out/f'chunk_{i:04d}.json'
            key={'media_sha256':fingerprint,'model':args.model,'device':args.device,'start':start,'end':end,
                 'local_model_sha256':weights_hash,'faster_whisper_version':library_version,
                 'algorithm':'overlap-midpoint-1s-v1'}
            cached=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
            if cached.get('key')==key and cached.get('status')=='completed':
                segments=cached['segments']; state='cached'
            else:
                audio=out/f'chunk_{i:04d}.wav'
                subprocess.run([ffmpeg,'-v','error','-ss',str(actual_start),'-i',str(media),'-t',str(actual_end-actual_start),
                                '-vn','-ar','16000','-ac','1','-y',str(audio)],check=True,capture_output=True)
                generated, info=model.transcribe(str(audio),language='zh',beam_size=3,vad_filter=True)
                segments=[]
                for s in generated:
                    a=actual_start+s.start; b=min(duration,actual_start+s.end)
                    midpoint=(a+b)/2
                    if start<=midpoint<end and b>a:
                        segments.append({'start':round(a,3),'end':round(b,3),'text':s.text.strip()})
                cache.write_text(json.dumps({'key':key,'status':'completed','segments':segments},ensure_ascii=False,indent=2),encoding='utf-8')
                state='completed'
            all_segments.extend(segments)
            log['chunks'].append({'index':i,'start_s':start,'end_s':end,'status':state,'segments':len(segments)})
            (out/'media_run.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
        transcript={'language':'zh','segments':sorted(all_segments,key=lambda x:x['start']),
                    'duration_s':duration,'media_sha256':fingerprint,'source':'local_faster_whisper',
                    'model':args.model}
        overlaps=[{'previous_index':i-1,'current_index':i,'overlap_s':round(transcript['segments'][i-1]['end']-s['start'],3)}
                  for i,s in enumerate(transcript['segments']) if i and s['start']<transcript['segments'][i-1]['end']]
        transcript['overlapping_segments_for_review']=overlaps
        log['overlapping_segment_pairs']=len(overlaps)
        (out/'transcript.json').write_text(json.dumps(transcript,ensure_ascii=False,indent=2),encoding='utf-8')
        frames=[]
        if has_video:
            frame_dir=out/'frames';frame_dir.mkdir(exist_ok=True)
            for i,t in enumerate(range(0,math.ceil(duration),args.frame_seconds)):
                target=frame_dir/f'frame_{i:04d}.jpg'
                if target.exists():target.unlink()
                subprocess.run([ffmpeg,'-v','error','-ss',str(t),'-i',str(media),'-frames:v','1','-y',str(target)],check=True,capture_output=True)
                if not target.exists(): raise ValueError(f'取帧未产生文件：{t}s')
                frames.append({'id':f'f{i:06d}','requested_time_s':t,'file':str(target.relative_to(out)),
                               'time_note':'解码器按请求位置取帧，尚未核验精确帧PTS'})
            log['frame_status']='completed'
        else: log['frame_status']='no_video_stream'
        (out/'frames.json').write_text(json.dumps(frames,ensure_ascii=False,indent=2),encoding='utf-8')
        log.update(status='completed',transcript_segments=len(all_segments),frames=len(frames))
    except Exception as exc:
        log.update(status='failed',error_type=type(exc).__name__,error=str(exc))
    log['elapsed_s']=round(time.perf_counter()-started,3)
    (out/'media_run.json').write_text(json.dumps(log,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(log,ensure_ascii=False))
    return 0 if log['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
