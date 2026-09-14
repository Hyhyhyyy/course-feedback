"""Shared server authority for model-dependent actions."""
def readiness(provider):
    if provider=='api':
        from api_settings import readiness as api_readiness
        return api_readiness()
    if provider=='local':
        from local_model import status
        live=status()
        return dict(text_ready=live['connected'],vision_ready=live['connected'],model=live['model'],reason='本地模型已连接' if live['connected'] else '本地模型未启动或连接异常')
    if provider=='campus':
        return dict(text_ready=False,vision_ready=False,model='',reason='校园服务器【待真实接入测试】，暂不开放分析')
    raise ValueError('未知运行方式')


def require_ready(provider,mode):
    state=readiness(provider)
    if not state['text_ready']:raise ValueError(state['reason'])
    if mode=='multimodal' and not state['vision_ready']:raise ValueError('当前仅通过文本验证，请完成图文验证或选择弹幕反馈分析')
    return state
