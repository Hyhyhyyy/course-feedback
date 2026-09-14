"""Read-only local preflight; never downloads platform media or fabricates inference."""
import argparse,json,sys,hashlib,importlib.util,datetime,time
from pathlib import Path

def main():
 parser=argparse.ArgumentParser()
 parser.add_argument("--config",required=True)
 parser.add_argument("--output",required=True)
 args=parser.parse_args()
 cfgpath=Path(args.config).resolve()
 cfg=json.loads(cfgpath.read_text(encoding="utf-8-sig"))
 started=time.perf_counter()
 checks=[]
 def add(name,status,details):
  checks.append({"name":name,"status":status,"details":details})
 add("full_scope","configured",{"requested_minutes":cfg["requested_minutes"],"scope":cfg["requested_scope"],"actual_duration_seconds":None,"duration_source":cfg["duration_source"]})
 for field in ("media_path","danmaku_path","permission_record_path"):
  val=cfg.get(field)
  if not val:
   add(field,"missing","未配置；不能据此认定材料不存在于本机其他位置")
   continue
  path=Path(val).expanduser()
  if not path.is_absolute():path=cfgpath.parent/path
  if not path.is_file():
   add(field,"missing","配置路径不是可读文件")
   continue
  h=hashlib.sha256()
  with path.open("rb") as f:
   for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
  add(field,"present_requires_validation",{"bytes":path.stat().st_size,"sha256":h.hexdigest()})
 add("model_configuration","configured_requires_probe" if cfg.get("model_base_url") and cfg.get("model_id") else "missing","本检查不发送材料或发起推理")
 modules={name:bool(importlib.util.find_spec(name)) for name in ("torch","transformers","faster_whisper","paddleocr","cv2")}
 add("python_packages","observed",modules)
 stages=[{"stage":s,"status":"not_run","reason":"真实材料与模型运行条件尚未落实"} for s in ("弹幕解析与全区间覆盖核验","音视频转写与画面索引","六类反馈及问题单元识别","片段关联与问题聚合","判定核验与摘要生成","交互报告与教师保存","整课复现")]
 result={"experiment_id":cfg["experiment_id"],"observed_at":datetime.datetime.now().astimezone().isoformat(),"python_executable":sys.executable,"status":"blocked_before_inference","checks":checks,"stages":stages,"inference_calls":0,"analyzed_comments":None,"processed_media_seconds":None,"elapsed_seconds":round(time.perf_counter()-started,3),"limitation":"前置检查程序，不是端到端分析系统。文件存在不等于许可有效或数据格式正确；模型配置不等于部署可用。"}
 out=Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
 out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
 print(json.dumps({"status":result["status"],"output":str(out),"checks":len(checks),"inference_calls":0},ensure_ascii=True))
 return 2
if __name__=="__main__":sys.exit(main())

