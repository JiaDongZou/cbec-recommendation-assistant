import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

const BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8000/api/v1';
async function api(path, options) {
  const response = await fetch(`${BASE}${path}`, { headers: { 'Content-Type': 'application/json' }, ...options });
  const body = await response.json();
  if (!response.ok) throw new Error(body.error?.message || `HTTP ${response.status}`);
  return body.data;
}
function useData(path) {
  const [state, setState] = useState({ loading: true, data: null, error: '' });
  useEffect(() => {
    let active = true;
    setState({ loading: true, data: null, error: '' });
    api(path).then(data => active && setState({ loading: false, data, error: '' }))
      .catch(error => active && setState({ loading: false, data: null, error: error.message }));
    return () => { active = false; };
  }, [path]);
  return state;
}
function Result({state, children}) {
  if (state.loading) return <div className="state">正在读取数据…</div>;
  if (state.error) return <div className="state error">请求失败：{state.error}</div>;
  if (!state.data || (Array.isArray(state.data) && !state.data.length)) return <div className="state">暂无数据</div>;
  return children(state.data);
}
const names = { click: '点击', cart: '加购', order: '下单', popularity: '热门', cooccurrence: '共现', hybrid: '融合' };
const date = ts => new Date(ts).toLocaleString('zh-CN', {timeZone:'UTC'});
function Card({title, children}) { return <section className="card"><h2>{title}</h2>{children}</section>; }
function Overview() {
  const state = useData('/overview');
  const top = useData('/items/top?metric=order&limit=5');
  return <><header><h1>运营总览</h1><p>用可追溯的行为数据，观察商品与推荐效果。</p></header><Result state={state}>{d => <><div className="notice">数据来源：{d.source} · 训练时间：{date(d.time_start)} 至 {date(d.time_end)} UTC · 验证会话 {d.validation_sessions}</div><div className="statgrid">{[['训练会话',d.train_sessions],['商品',d.items],['行为',d.events],['下单行为',d.orders],['下单/加购行为比',d.cart_to_order_ratio ?? '—'],['最佳 order NDCG@10',d.best_order_ndcg_at_10?.ndcg ?? '—']].map(([label,value])=><div className="stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div></>}</Result><Card title="热门下单商品"><Result state={top}>{rows => <div className="rows">{rows.map((r,i)=><div className="row" key={r.item_id}><span>#{i+1}　商品 {r.item_id}</span><strong>{r.count} 次行为</strong></div>)}</div>}</Result></Card></>;
}
function Recommend() {
  const samples = useData('/sessions?limit=10');
  const [id,setId] = useState(''); const [target,setTarget]=useState('order'); const [model,setModel]=useState('hybrid');
  useEffect(()=>{if(samples.data?.length && !id) setId(String(samples.data[0].session_id));},[samples.data]);
  const session = useData(id ? `/sessions/${id}` : '/sessions?limit=1');
  const recs = useData(id ? `/recommendations/${id}?k=10&target=${target}&model=${model}` : '/sessions?limit=1');
  return <><header><h1>推荐工作台</h1><p>选一个匿名会话，查看可见行为和 Top 10 推荐。</p></header><div className="controls"><label>会话 ID <input value={id} onChange={e=>setId(e.target.value)} list="sessions" /></label><datalist id="sessions">{samples.data?.map(s=><option key={s.session_id} value={s.session_id}/>)}</datalist><label>目标 <select value={target} onChange={e=>setTarget(e.target.value)}>{Object.keys(names).slice(0,3).map(t=><option value={t} key={t}>{names[t]}</option>)}</select></label><label>策略 <select value={model} onChange={e=>setModel(e.target.value)}>{['popularity','cooccurrence','hybrid'].map(m=><option value={m} key={m}>{names[m]}</option>)}</select></label></div><div className="two"><Card title="会话行为"><Result state={session}>{d => <div className="timeline">{d.events.map((e,i)=><div key={i}><b>{names[e.type]}</b><span>商品 {e.aid}</span><small>{date(e.ts)} UTC</small></div>)}</div>}</Result></Card><Card title="推荐商品"><Result state={recs}>{d => d.results.length ? <div className="rows">{d.results.map(r=><div className="rec" key={r.item_id}><div><b>#{r.rank} 商品 {r.item_id}</b><strong>{r.score.toFixed(3)}</strong></div><p>{r.reasons.join(' · ')}</p></div>)}</div> : <div className="state">当前条件下没有候选商品</div>}</Result></Card></div></>;
}
function Items() {
  const top = useData('/items/top?metric=order&limit=10'); const [id,setId]=useState('');
  useEffect(()=>{if(top.data?.length && !id) setId(String(top.data[0].item_id));},[top.data]);
  const stats = useData(id ? `/items/${id}/stats` : '/items/top?metric=order&limit=1');
  const related = useData(id ? `/items/${id}/related?limit=8` : '/items/top?metric=order&limit=1');
  return <><header><h1>商品分析</h1><p>查看行为漏斗、按日趋势和关联商品。</p></header><div className="controls"><label>商品 ID <input value={id} onChange={e=>setId(e.target.value)}/></label></div><Result state={stats}>{d => <><div className="statgrid">{[['点击',d.clicks],['加购',d.carts],['下单',d.orders],['加购/点击行为比',d.click_to_cart_ratio ?? '—'],['下单/加购行为比',d.cart_to_order_ratio ?? '—']].map(([label,value])=><div className="stat" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div><Card title="按日行为趋势"><div className="rows">{d.trend.map(r=><div className="row" key={r.date}><span>{r.date}</span><span>点击 {r.click}　加购 {r.cart}　下单 {r.order}</span></div>)}</div></Card></>}</Result><Card title="共同出现商品"><Result state={related}>{rows => rows.length ? <div className="rows">{rows.map(r=><div className="row" key={r.item_id}><span>商品 {r.item_id}</span><strong>加权分 {r.cooccurrence_score}</strong></div>)}</div> : <div className="state">没有关联商品</div>}</Result></Card></>;
}
function Evaluation() {
  const state=useData('/metrics/evaluation'); const [target,setTarget]=useState('order'); const [k,setK]=useState(10);
  return <><header><h1>模型评估</h1><p>同一验证窗口，对比三种可解释策略。</p></header><div className="controls"><label>目标 <select value={target} onChange={e=>setTarget(e.target.value)}>{['click','cart','order'].map(t=><option key={t} value={t}>{names[t]}</option>)}</select></label><label>K <select value={k} onChange={e=>setK(Number(e.target.value))}>{[5,10,20].map(n=><option key={n}>{n}</option>)}</select></label></div><Result state={state}>{d => <><div className="notice">{d.split}<br/>{d.note}</div><Card title="离线指标"><div className="tablewrap"><table><thead><tr><th>策略</th><th>Recall@{k}</th><th>MRR@{k}</th><th>NDCG@{k}</th><th>有效会话</th></tr></thead><tbody>{d.results.filter(r=>r.target===target&&r.k===k).map(r=><tr key={r.model}><td>{names[r.model]}</td><td>{r.recall ?? '—'}</td><td>{r.mrr ?? '—'}</td><td>{r.ndcg ?? '—'}</td><td>{r.samples}</td></tr>)}</tbody></table></div></Card></>}</Result></>;
}
const prompts=['哪些商品适合做组合推荐？','最热门的商品是什么？','加购到下单情况如何？','哪种推荐模型效果更好？','生成运营日报'];
function Assistant() {
  const [question,setQuestion]=useState(prompts[0]); const [state,setState]=useState({loading:false,data:null,error:''});
  async function submit(value=question) {setQuestion(value);setState({loading:true,data:null,error:''});try{setState({loading:false,data:await api('/agent/chat',{method:'POST',body:JSON.stringify({question:value})}),error:''});}catch(e){setState({loading:false,data:null,error:e.message});}}
  return <><header><h1>AI 运营助手</h1><p>基于内部统计工具生成结论、证据和下一步行动。</p></header><div className="chips">{prompts.map(p=><button key={p} onClick={()=>submit(p)}>{p}</button>)}</div><form className="ask" onSubmit={e=>{e.preventDefault();submit();}}><input value={question} onChange={e=>setQuestion(e.target.value)} placeholder="输入运营问题"/><button disabled={state.loading}>分析</button></form>{state.loading&&<div className="state">正在分析…</div>}{state.error&&<div className="state error">{state.error}</div>}{state.data&&<><Card title="结论"><p>{state.data.answer}</p></Card>{[['证据',state.data.evidence],['建议行动',state.data.actions],['风险与限制',state.data.risks]].map(([title,rows])=><Card title={title} key={title}>{rows.length?<ul>{rows.map((r,i)=><li key={i}>{r}</li>)}</ul>:<p>无可用证据</p>}</Card>)}<details><summary>查看工具调用</summary><pre>{JSON.stringify(state.data.tool_calls,null,2)}</pre></details></>}</>;
}
const tabs=[['总览',Overview],['推荐工作台',Recommend],['商品分析',Items],['模型评估',Evaluation],['运营助手',Assistant]];
function App(){const [active,setActive]=useState(0);const Page=tabs[active][1];return <div className="shell"><aside><div className="brand"><span>CBEC</span><small>Recommendation Studio</small></div><nav>{tabs.map(([name],i)=><button key={name} className={i===active?'active':''} onClick={()=>setActive(i)}>{name}</button>)}</nav><div className="asidefoot">匿名会话 · 本地演示</div></aside><main><Page/></main></div>}
createRoot(document.getElementById('root')).render(<App/>);
