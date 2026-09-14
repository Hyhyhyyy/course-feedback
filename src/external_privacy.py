"""Conservative extra masking before remote inference; not a complete PII detector."""
import re
from course_feedback.pipeline import redact


def mask(value):
    if isinstance(value,str):
        text=redact(value)
        return re.sub(r'我[^，。！？\n]{1,60}实名', '[自报身份已遮盖]实名',text)
    if isinstance(value,list):return [mask(item) for item in value]
    if isinstance(value,dict):return {key:mask(item) for key,item in value.items()}
    return value
