"""Course-native audiovisual evidence preparation, independent of external projects.
Decode bounded scope -> timestamped ASR -> slide-change candidates -> evidence index.
"""
import argparse,json,math,subprocess,time
from pathlib import Path
from fetch_course import save_json
from course_feedback.pipeline import digest

VERSION='course-av-1'

def boundary_candidates(samples,end,min_gap=30,max_gap=180,threshold=.14):
    boundaries=[{'start_s':0.0,'reason':'course_start'}]
    for t,score in samples:
        gap=t-boundaries[-1]['start_s']
        if t>=end:break
        if gap>=max_gap or (gap>=min_gap and score>=threshold):
            boundaries.append({'start_s':t,'reason':'visual_change' if score>=threshold else 'maximum_span'})
    return [dict(b,end_s=boundaries[i+1]['start_s'] if i+1<len(boundaries) else end) for i,b in enumerate(boundaries)]

def prepare(media,out,model_path,max_seconds=None):
    import av,numpy as np,imageio_ffmpeg
    from faster_whisper import WhisperModel
    media=Path(media);out=Path(out);out.mkdir(parents=True,exist_ok=True);started=time.perf_counter()
    log={'status':'running','version':VERSION,'chunks':[],'frame_status':'pending'}
    def update(**values):log.update(values);save_json(out/'media_run.json',log)
    try:
        with av.open(str(media)) as c:
            duration=c.duration/av.time_base
            if not c.streams.audio or not c.streams.video:raise ValueError('课程需包含音轨和视频')
        end=min(duration,float(max_seconds)) if max_seconds is not None else duration
        if not math.isfinite(end) or end<=0:raise ValueError('分析范围无效')
        fingerprint=digest(media);weights=Path(model_path)/'model.bin'
        if not weights.is_file():raise ValueError('请安装本地语音模型')
        key={'version':VERSION,'media':fingerprint,'weights':digest(weights),'end':end}
        update(duration_s=end,source_duration_s=duration,key=key,scope='仅处理所选范围；画面变化为分段候选，不等于知识点边界')
        asr=None;segments=[];ffmpeg=imageio_ffmpeg.get_ffmpeg_exe()
        for i,start in enumerate(range(0,math.ceil(end),180)):
            finish=min(end,start+180);cache=out/f'asr_{i:04d}.json';cache_key=dict(key,start=start,finish=finish)
            previous=json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else {}
            if previous.get('key')==cache_key:
                rows=previous['segments'];state='cached'
            else:
                if asr is None:asr=WhisperModel(str(model_path),device='cpu',compute_type='int8')
                a=max(0,start-1);b=min(end,finish+1);audio=out/f'audio_{i:04d}.wav'
                subprocess.run([ffmpeg,'-v','error','-ss',str(a),'-i',str(media),'-t',str(b-a),'-vn','-ar','16000','-ac','1','-y',str(audio)],check=True,capture_output=True)
                result,_=asr.transcribe(str(audio),language='zh',beam_size=3,vad_filter=True,word_timestamps=True)
                rows=[]
                for seg in result:
                    x=a+seg.start;y=min(end,a+seg.end)
                    if start<=(x+y)/2<finish and y>x:
                        rows.append({'start':round(x,3),'end':round(y,3),'text':seg.text.strip(),'avg_logprob':seg.avg_logprob,'no_speech_prob':seg.no_speech_prob})
                save_json(cache,{'key':cache_key,'segments':rows});state='completed'
            segments.extend(rows);log['chunks'].append({'start_s':start,'end_s':finish,'status':state,'segments':len(rows)});update()
        segments.sort(key=lambda r:r['start']);save_json(out/'transcript.json',{'segments':segments,'duration_s':end,'source':'course_local_asr','model':str(model_path),'version':VERSION})
        update(frame_status='scanning_visual_changes')
        samples=[];small_previous=None
        with av.open(str(media)) as c:
            stream=c.streams.video[0]
            for requested in range(0,math.ceil(end),5):
                c.seek(int(requested/float(stream.time_base)),stream=stream,backward=True)
                frame=next((f for f in c.decode(stream) if f.time is not None and f.time>=requested),None)
                if frame is None or frame.time>=end:continue
                tiny=frame.to_image().convert('L').resize((96,54));arr=np.asarray(tiny,dtype=float)/255
                score=float(np.mean(np.abs(arr-small_previous))) if small_previous is not None else 0
                small_previous=arr;samples.append((float(frame.time),score))

        windows=boundary_candidates(samples,end);frame_dir=out/'frames';frame_dir.mkdir(exist_ok=True);frames=[]
        with av.open(str(media)) as c:
            stream=c.streams.video[0]
            for i,w in enumerate(windows):
                requested=min(w['start_s']+5,(w['start_s']+w['end_s'])/2)
                c.seek(int(requested/float(stream.time_base)),stream=stream,backward=True)
                frame=next((f for f in c.decode(stream) if f.time is not None and f.time>=requested),None)
                if frame is None or frame.time>=end:continue
                actual=float(frame.time);img=frame.to_image();img.thumbnail((1280,720));name=f'frames/evidence_{i:04d}.jpg';img.save(out/name,quality=88)
                frames.append({'id':f'f{i:06d}','requested_time_s':actual,'actual_time_s':actual,'file':name,'time_note':'使用解码帧PTS定位','boundary_reason':w['reason']})
        save_json(out/'frames.json',frames);save_json(out/'windows.json',{'windows':windows,'method':'灰度画面差异候选，最短30秒、最长180秒；非知识点真值','samples':[{'time_s':t,'change':v} for t,v in samples]})
        update(status='completed',frame_status='completed',transcript_segments=len(segments),frames=len(frames),elapsed_s=round(time.perf_counter()-started,3))
    except Exception as e:update(status='failed',error=str(e));raise
    return log

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--media',required=True);p.add_argument('--out',required=True);p.add_argument('--model',required=True);p.add_argument('--max-seconds',type=float);a=p.parse_args();prepare(a.media,a.out,a.model,a.max_seconds)
