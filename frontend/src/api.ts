const BASE=import.meta.env.VITE_API_BASE || (import.meta.env.PROD ? 'https://resumepilot-api-lvf3.onrender.com' : 'http://127.0.0.1:8000');
export type Change={id:number;section:string;original_text:string;proposed_text:string;rationale:string;status:'pending'|'approved'|'rejected'};
export type Project={id:number;title:string;original_filename:string;original_text:string;job_description:string;changes:Change[];generation_mode?:string;notice?:string};
export type Summary={id:number;title:string;original_filename:string;created_at:string};
async function req<T>(path:string,token:string,init:RequestInit={}):Promise<T>{const form=init.body instanceof FormData;const r=await fetch(BASE+path,{...init,headers:{...(form?{}:{'Content-Type':'application/json'}),...(token?{Authorization:`Bearer ${token}`}:{})}});if(!r.ok){let msg=`Request failed (${r.status})`;try{msg=(await r.json()).detail||msg}catch{}throw new Error(msg)}if((r.headers.get('content-type')||'').includes('application/pdf')||(r.headers.get('content-type')||'').includes('wordprocessingml'))return await r.blob() as T;return r.json()}
export const auth=(mode:'login'|'register',email:string,password:string)=>req<{token:string}>('/api/auth/'+mode,'',{method:'POST',body:JSON.stringify({email,password})});
export const list=(t:string)=>req<Summary[]>('/api/projects',t);
export const get=(t:string,id:number)=>req<Project>(`/api/projects/${id}`,t);
export async function create(t:string,file:File,jd:string,title:string){const f=new FormData();f.append('file',file);f.append('job_description',jd);f.append('title',title);return req<Project>('/api/projects',t,{method:'POST',body:f})}
export const generate=(t:string,id:number)=>req<Project>(`/api/projects/${id}/generate`,t,{method:'POST'});
export async function decide(t:string,pid:number,cid:number,decision:'approved'|'rejected'){const f=new FormData();f.append('decision',decision);return req<Project>(`/api/projects/${pid}/changes/${cid}/decision`,t,{method:'POST',body:f})}
export async function download(t:string,id:number,fmt:'pdf'|'docx'){const b=await req<Blob>(`/api/projects/${id}/export/${fmt}`,t);const u=URL.createObjectURL(b);const a=document.createElement('a');a.href=u;a.download=`resumepilot-approved-resume.${fmt}`;a.click();URL.revokeObjectURL(u)}
