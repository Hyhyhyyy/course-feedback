"""Server-side inference profiles. Credentials never enter browser responses."""
import os


def settings(provider):
    if provider == 'api':
        from api_settings import CONFIG, snapshot
        if CONFIG:
            return snapshot()
    if provider == 'local':
        return dict(model='qwen35-4b', url='http://127.0.0.1:8081/v1', key='')
    if provider not in ('api', 'campus'):
        raise ValueError('未知模型运行方式')
    prefix = 'COURSE_API' if provider == 'api' else 'COURSE_CAMPUS'
    url = os.environ.get(prefix+'_BASE_URL', '').rstrip('/')
    model = os.environ.get(prefix+'_MODEL', '')
    key = os.environ.get(prefix+'_KEY', '')
    if not url or not model:
        raise ValueError('请先在服务器配置 '+prefix+'_BASE_URL 和 '+prefix+'_MODEL')
    if not url.startswith('https://') and not url.startswith('http://127.0.0.1:'):
        raise ValueError('远程模型连接必须使用 HTTPS')
    return dict(model=model, url=url, key=key)
