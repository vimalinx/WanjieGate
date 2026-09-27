// Runtime's supported JSON Schema subset; extension state stays bounded and typed.
export function validateComponent(value,schema={},path='$'){
 const fail=reason=>{throw new Error(`${path}: ${reason}`);};
 if(schema.const!==undefined&&JSON.stringify(value)!==JSON.stringify(schema.const))fail('unexpected constant');
 if(schema.enum&&!schema.enum.some(x=>JSON.stringify(x)===JSON.stringify(value)))fail('unsupported value');
 const type=value===null?'null':Array.isArray(value)?'array':typeof value;
 if(schema.type&&!(schema.type===type||schema.type==='integer'&&Number.isInteger(value)))fail('expected '+schema.type);
 if(type==='object'){
  for(const key of schema.required||[])if(!Object.hasOwn(value,key))fail('missing '+key);
  for(const [key,child] of Object.entries(value)){
   if(Object.hasOwn(schema.properties||{},key))validateComponent(child,schema.properties[key],path+'.'+key);
   else if(schema.additionalProperties===false)fail('unknown '+key);
   else if(typeof schema.additionalProperties==='object')validateComponent(child,schema.additionalProperties,path+'.'+key);
  }
 }
 if(type==='array'){
  if(value.length<(schema.minItems??0)||value.length>(schema.maxItems??10000))fail('array length');
  value.forEach((x,i)=>validateComponent(x,schema.items||{},`${path}[${i}]`));
 }
 if(type==='string'&&(value.length<(schema.minLength??0)||value.length>(schema.maxLength??200000)||schema.pattern&&!new RegExp(schema.pattern).test(value)))fail('invalid text');
 if(type==='number'&&(!Number.isFinite(value)||value<(schema.minimum??-Infinity)||value>(schema.maximum??Infinity)))fail('invalid number');
 return value;
}
