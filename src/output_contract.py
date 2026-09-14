"""Validate the deliberately small JSON-schema subset used by this pipeline."""
def validate(value, schema):
    supported={'type','properties','required','additionalProperties','items','enum','minItems','maxItems','minLength','maxLength'}
    if set(schema)-supported:raise ValueError('输出结构使用了未实现的约束')
    kind=schema.get('type')
    types={'object':dict,'array':list,'string':str,'integer':int,'boolean':bool}
    if kind not in types or type(value) is not types[kind]:raise ValueError('模型输出类型不符合约定')
    if 'enum' in schema and value not in schema['enum']:raise ValueError('模型输出值超出允许范围')
    if kind=='object':
        props=schema.get('properties',{})
        if not set(schema.get('required',[]))<=set(value):raise ValueError('模型输出缺少必要字段')
        if schema.get('additionalProperties') is False and set(value)-set(props):raise ValueError('模型输出包含未知字段')
        for key,item in value.items():
            if key in props:validate(item,props[key])
    if kind in ('array','string'):
        suffix='Items' if kind=='array' else 'Length'
        if len(value)<schema.get('min'+suffix,0) or len(value)>schema.get('max'+suffix,float('inf')):
            raise ValueError('模型输出长度不符合约定')
    if kind=='array':
        for item in value:validate(item,schema['items'])
