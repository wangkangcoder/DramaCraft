import{L as De,M as Ue,u as xt,i as C,A as l,z as pe,o as At,G as ve,N as Tt,c as x,d as n,t as k,e as w,w as f,p as se,h as H,J as Ge,K as Oe,O as Rt,F as Ee,C as Ne,P as Et,k as b,x as o,Q as Nt,H as fe,m as y,g,I as zt}from"./index-b73bff7d.js";import{i as $t}from"./index-6433f102.js";import{n as It,c as Lt,d as Ft,b as Pt,e as Vt,s as Bt,k as Mt,a as Ht,f as Wt,j as Gt,r as Ot}from"./scriptText-044004f8.js";import{c as qt}from"./ai-5a2aea6c.js";import{_ as Dt}from"./_plugin-vue_export-helper-c27b6911.js";const Ut=/^第[一二三四五六七八九十百零\d]+幕[·.、-]?第[一二三四五六七八九十百零\d]+节$/,Jt=/^第[一二三四五六七八九十百零\d]+场$/,jt=["内景","外景","内外景","外内景","画外音"];function U(L){return String(L||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;")}function Kt(L){const m=String(L||"").trim();return jt.some(S=>m.startsWith(S))}function K(L){const m=String(L||"").trim();return m?Ut.test(m)?"act-section":Jt.test(m)?"scene-number":Kt(m)?"scene-heading":"body":"spacer"}function Yt(L){const m=De(L).split(`
`),S=[];for(let d=0;d<m.length;d+=1){const A=m[d],W=K(A);if(W==="spacer"){S.push('<div class="spacer"></div>');continue}if(W==="scene-number"){let B=d+1;for(;B<m.length&&K(m[B])==="spacer";)B+=1;const ie=m[B]||"";if(K(ie)==="scene-heading"){for(S.push(`<div class="scene-block"><div class="scene-meta scene-number">${U(A)}</div><div class="scene-meta scene-heading">${U(ie)}</div></div>`),d=B;d+1<m.length&&K(m[d+1])==="spacer";)d+=1;continue}for(S.push(`<div class="scene-block"><div class="scene-meta scene-number">${U(A)}</div></div>`);d+1<m.length&&K(m[d+1])==="spacer";)d+=1;continue}if(W==="scene-heading"){for(S.push(`<div class="scene-block"><div class="scene-meta scene-heading">${U(A)}</div></div>`);d+1<m.length&&K(m[d+1])==="spacer";)d+=1;continue}S.push(`<p class="line ${W}">${U(A)}</p>`)}return S.join("")}function qe({title:L,content:m}){const S=De(m);if(!S)return!1;const d=Ue(L,S),A=window.open("","_blank");if(!A)return!1;const W=`<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>${U(d)}.pdf</title>
    <style>
      @page {
        size: A4;
        margin: 18mm 16mm 18mm;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        color: #111827;
        background: #f3f4f6;
        font-family: "Microsoft YaHei", "PingFang SC", "Noto Sans CJK SC", "SimSun", sans-serif;
      }

      .page {
        width: 210mm;
        min-height: 297mm;
        margin: 0 auto;
        padding: 18mm 16mm;
        background: #ffffff;
      }

      .title {
        margin: 0 0 12mm;
        text-align: center;
        font-size: 26px;
        line-height: 1.35;
        font-weight: 700;
        letter-spacing: 0.04em;
      }

      .content {
        color: #111827;
      }

      .line {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .act-section {
        margin-top: 9mm;
        margin-bottom: 3mm;
        font-size: 18px;
        line-height: 1.55;
        font-weight: 700;
        page-break-after: avoid;
      }

      .scene-number,
      .scene-heading {
        font-size: 16px;
        line-height: 1.8;
        font-weight: 400;
      }

      .scene-block {
        margin-bottom: 4.5mm;
        page-break-after: avoid;
      }

      .scene-meta {
        margin: 0;
        white-space: pre-wrap;
        word-break: break-word;
      }

      .scene-block .scene-number,
      .scene-block .scene-heading {
        margin: 0;
      }

      .body {
        font-size: 13px;
        line-height: 1.92;
        font-weight: 400;
      }

      .spacer {
        height: 4mm;
      }

      @media print {
        body {
          background: #ffffff;
        }

        .page {
          width: auto;
          min-height: auto;
          margin: 0;
          padding: 0;
        }
      }
    </style>
  </head>
  <body>
    <main class="page">
      <h1 class="title">${U(d)}</h1>
      <section class="content">${Yt(S)}</section>
    </main>
    <script>
      window.onload = function () {
        setTimeout(function () {
          window.focus();
          window.print();
        }, 150);
      };
    <\/script>
  </body>
</html>`;try{A.document.open(),A.document.write(W),A.document.close()}catch(B){return console.error(B),A.close(),!1}return!0}const Qt={class:"editor-page"},Xt={class:"hero"},Zt={class:"hero-actions"},en={class:"chip"},tn={class:"metrics"},nn={class:"metric"},an={class:"metric"},ln={class:"metric"},sn={key:0,class:"done-banner"},rn={key:0,class:"done-actions"},on={class:"layout"},cn={class:"main-col"},un={class:"card editor-card"},dn={class:"card-head"},pn={class:"pill"},vn={class:"editor-toolbar"},fn={class:"toolbar-group"},mn={class:"toolbar-group"},gn={class:"rich-shell"},hn={class:"card advice-card"},yn={class:"card-head light"},wn={class:"advice-actions"},Cn={class:"advice-body"},kn={key:0,class:"review-grid"},bn={class:"review-card"},_n={class:"review-summary"},Sn={key:0,class:"review-ok"},xn={class:"review-card"},An={class:"review-summary"},Tn={key:0},Rn={key:0,class:"review-ok"},En={key:1,class:"revision-box"},Nn=["value"],zn={key:2},$n={class:"card graph-card"},In={key:1,class:"version-list"},Ln={class:"version-head"},Fn={class:"version-meta"},Pn={class:"version-preview"},ze="AI_SCREENPLAY_VERSIONS_V2",Vn={__name:"EditorView",setup(L){const m=xt(),S=C(null),d=C(null),A=C(null),W=/^第[一二三四五六七八九十百零\d]+幕[·.、-]?第[一二三四五六七八九十百零\d]+节$/,B=/^第[一二三四五六七八九十百零\d]+场$/,ie=/^[\u4e00-\u9fff]{2,6}$/,$e=(t="")=>String(t).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;").replace(/'/g,"&#39;"),r=(t,e=!0)=>It(t,{trim:e}),me=(t,e)=>Vt(t,e),Ie=(t=i.value)=>Ue(l.title,t),i=C(r(l.scriptContent||"",!1)),F=C("rich"),re=C(!1),P=C(String(l.editorRichContent||"")),Y=C("init"),G=C(!1),Q=C(!1),J=C([]),ge=C(null),_=C(null),E=C(null),he=C(!1),ye=C(!1),we=C(!1),X=C(!1),N=C(l.pipelineCompletionSnapshot||null),O=b(()=>l.pipelineScriptFormat||"movie"),Je=b(()=>Ot(O.value)==="series"),q=b(()=>!!l.pipelineLatestActReviewed),Le=b(()=>!!l.pipelineGenerationInFlight),oe=b(()=>G.value||Le.value),je=b(()=>Le.value&&!G.value),Fe=b(()=>({characters:(i.value||"").length,paragraphs:(i.value||"").split(`
`).map(t=>t.trim()).filter(Boolean).length})),Ke=b(()=>{var t,e,a;return!!(l.pipelineIsScriptEnd||(t=N.value)!=null&&t.is_complete||(e=N.value)!=null&&e.generation_locked||((a=N.value)==null?void 0:a.can_continue)===!1)}),Ye=b(()=>Mt(N.value,i.value,O.value)),Z=b(()=>Ht(N.value,O.value,i.value)),z=b(()=>Ke.value),Pe=b(()=>z.value&&Je.value),Ce=b(()=>r(i.value)?Wt(N.value,i.value,{scriptFormat:O.value,latestActReviewed:q.value}):"尚未生成剧本"),ke=b(()=>Gt(N.value||l.pipelineCompletionSnapshot||null,q.value)),ce=b(()=>z.value?ke.value:"当前剧本仍在推进中。"),Qe=b(()=>!oe.value&&!z.value&&!!r(i.value)),Xe=b(()=>oe.value?`正在生成${l.pipelineGenerationTargetAct||Z.value||"下一幕"}`:z.value?q.value?"已完结":"已完结（未修改）":"生成下一幕"),Ze=b(()=>G.value?`正在生成${Z.value||"下一幕"}`:je.value?`正在生成${l.pipelineGenerationTargetAct||Z.value||"下一幕"}`:z.value?q.value?"已完结，可生成 PDF":"已完结（未修改）":Ce.value),et=b(()=>oe.value?"生成中":z.value?q.value?"已完结":"已完结（未修改）":q.value?"当前幕已确认":"当前幕待复核"),be=()=>{_.value=null,E.value=null},tt=(t="")=>{const e=String(t).trim();return e?W.test(e)?"act":B.test(e)?"scene-number":e.startsWith("内景")||e.startsWith("外景")?"scene-heading":ie.test(e)?"speaker":"body":"spacer"},nt=(t="")=>{const e=r(t,!1);return(e?e.split(`
`):[""]).map(v=>{const s=tt(v);return s==="spacer"?'<div class="rich-line rich-spacer"><br></div>':`<div class="rich-line rich-${s}">${$e(v)||"<br>"}</div>`}).join("")},_e=(t=i.value)=>nt(t),j=()=>{var e;const t=String(((e=d.value)==null?void 0:e.innerHTML)||"");P.value=t||_e(i.value),l.editorRichContent=P.value},D=(t=i.value)=>{P.value=_e(t),l.editorRichContent=P.value},ee=()=>{var e;const t=String(((e=d.value)==null?void 0:e.innerText)||"").replace(/\u00A0/g," ").replace(/\r\n/g,`
`).replace(/\r/g,`
`);return r(t,!1)},ue=()=>{if(!d.value||re.value)return;const t=P.value||_e(i.value);d.value.innerHTML!==t&&(d.value.innerHTML=t)},Ve=async t=>{var e;t!==F.value&&(F.value==="rich"&&($(ee(),{preserveWhitespace:!0,source:"rich"}),j()),F.value=t,await ve(),F.value==="rich"?ue():(e=A.value)==null||e.focus())},$=(t,{preserveWhitespace:e=!1,source:a="plain"}={})=>{Y.value=a,i.value=r(t,!e),l.scriptContent=r(i.value)},at=()=>{j(),$(ee(),{preserveWhitespace:!0,source:"rich"})},lt=()=>{re.value=!0},st=()=>{re.value=!1,j(),$(ee(),{preserveWhitespace:!0,source:"rich"})},Se=()=>{var a;if(F.value!=="rich")return o.info("强调和高亮仅在可视化排版模式下可用。"),!1;(a=d.value)==null||a.focus();const t=window.getSelection();return!(t&&t.rangeCount>0&&String(t.toString()||"").trim())?(o.info("请先在可视化排版区域选中需要标记的文字。"),!1):!0},xe=()=>{j(),$(ee(),{preserveWhitespace:!0,source:"rich"})},it=()=>{Se()&&(document.execCommand("bold",!1),xe())},rt=()=>{Se()&&(document.execCommand("styleWithCSS",!1,!0),document.execCommand("foreColor",!1,"#7ee7ff"),xe())},ot=()=>{Se()&&(document.execCommand("removeFormat",!1),xe())},de=t=>{var e,a,v;if(t){if(F.value==="plain"){const s=A.value,c=i.value||"",u=(s==null?void 0:s.selectionStart)??c.length,T=(s==null?void 0:s.selectionEnd)??c.length,V=`${c.slice(0,u)}${t}${c.slice(T)}`;P.value="",l.editorRichContent="",$(V,{preserveWhitespace:!0,source:"plain"}),ve(()=>{if(!s)return;s.focus();const R=u+t.length;s.setSelectionRange(R,R)});return}if((e=d.value)==null||e.focus(),(a=document.queryCommandSupported)!=null&&a.call(document,"insertText"))document.execCommand("insertText",!1,t);else{const s=window.getSelection();if(!(s!=null&&s.rangeCount))(v=d.value)==null||v.append(document.createTextNode(t));else{const c=s.getRangeAt(0);c.deleteContents(),c.insertNode(document.createTextNode(t)),c.collapse(!1),s.removeAllRanges(),s.addRange(c)}}j(),$(ee(),{preserveWhitespace:!0,source:"rich"})}},ct=()=>[...String(i.value||"").matchAll(/第([一二三四五六七八九十百零\d]+)场/g)].length+1,ut=()=>{const t=Ye.value||"第一幕";de(`${t}·第1节
`)},dt=()=>{de(`第${ct()}场
`)},Be=t=>{de(`${t} 场所 时间
`)},pt=()=>{de(`角色名
对话内容
`)},vt=()=>{const t=r(i.value,!1);D(t),$(t,{preserveWhitespace:!0,source:"plain"}),ve(()=>ue()),o.success("剧本文本已按当前规则重新整理。")};let I=null,te=null,Me="";const ft=t=>{var e,a;return r(((e=t==null?void 0:t.data)==null?void 0:e.scriptContent)||((a=t==null?void 0:t.data)==null?void 0:a.pipelineRequirements)||"暂无内容").slice(0,180)||"暂无内容"},He=()=>{try{const t=localStorage.getItem(ze);J.value=t?JSON.parse(t).versions||[]:[]}catch(t){console.error(t),J.value=[]}},ne=(t=null)=>{const e=t?{...t}:null;N.value=e,l.pipelineCompletionSnapshot=e;const a=!!(e!=null&&e.generation_locked||(e==null?void 0:e.can_continue)===!1),v=!!(e!=null&&e.is_complete||a);l.pipelineIsScriptEnd=v,l.pipelineCompletionReason=String((e==null?void 0:e.reason)||"")},Ae=t=>{var v;if(!I)return;const e={nodes:[{id:"scene:当前场景",name:"当前场景",category:1},{id:"char:主角",name:"主角",category:0}],links:[{source:"char:主角",target:"scene:当前场景",name:"出现在"}]},a=(v=t==null?void 0:t.nodes)!=null&&v.length?t:e;I.setOption({backgroundColor:"transparent",tooltip:{formatter:"{b}"},series:[{type:"graph",layout:"force",roam:!0,draggable:!0,force:{repulsion:260,edgeLength:110},label:{show:!0,position:"right",formatter:"{b}",color:"#eef4ff"},edgeSymbol:["circle","arrow"],edgeSymbolSize:[4,10],edgeLabel:{show:!0,fontSize:10,formatter:"{c}",color:"#9eb0c8"},data:(a.nodes||[]).map(s=>({...s,symbolSize:s.category===0?54:s.category===2?34:42})),links:(a.links||[]).map(s=>({...s,value:s.name})),categories:[{name:"角色"},{name:"场景"},{name:"伏笔"}],lineStyle:{color:"#7f8da3",curveness:.12}}]},!0)},Te=async t=>{var a;if(!I)return;const e=r(t);if(!e){Ae(null);return}try{const v=await Bt(e);Ae((a=v.data)==null?void 0:a.data)}catch(v){console.error(v)}},mt=t=>{te&&clearTimeout(te),te=setTimeout(()=>{const e=r(t);!e||e===Me||(Me=e,Te(e))},1200)},gt=async()=>{if(S.value){I=$t(S.value),I.showLoading({text:"正在同步剧情状态网络...",color:"#4f8cff",textColor:"#d7e6ff",maskColor:"rgba(9, 21, 40, 0.24)"});try{await Te(l.scriptContent||i.value)}finally{I.hideLoading()}}},ht=async t=>{var e,a,v;ge.value=t.id;try{const s=localStorage.getItem(ze),c=JSON.parse(s);c.currentVersionId=t.id,localStorage.setItem(ze,JSON.stringify(c)),t.data&&Object.assign(l,t.data);const u=r(l.scriptContent||((e=t.data)==null?void 0:e.scriptContent)||"",!1);P.value=String(l.editorRichContent||((a=t.data)==null?void 0:a.editorRichContent)||""),P.value||D(u),$(u,{preserveWhitespace:!0,source:"external"}),be(),ne(l.pipelineCompletionSnapshot||((v=t.data)==null?void 0:v.pipelineCompletionSnapshot)||null),Q.value=!1,o.success(`已恢复到 ${t.savedAtReadable}`)}catch(s){console.error(s),o.error("恢复失败，请重试。")}finally{ge.value=null}},yt=async()=>{var e;const t=r(i.value);if(!t){o.warning("请先准备当前幕正文，再生成 AI 优化建议。");return}he.value=!0,_.value=null,E.value=null;try{const a=await Lt(t,l.pipelineOutline||"",l.pipelineCharacters||"",l.pipelineRequirements||"",O.value);if(_.value=((e=a==null?void 0:a.data)==null?void 0:e.analysis)||null,!_.value)throw new Error("当前幕优化建议结果为空");_.value.has_issues?(l.pipelineLatestActReviewed=!1,o.warning("已生成当前幕优化建议，可以继续一键生成优化版本。")):(l.pipelineLatestActReviewed=!0,o.success(z.value?ke.value:"当前幕暂时没有明显需要优化的地方。"))}catch(a){console.error(a),o.warning(me(a,"当前幕优化建议生成失败，请稍后重试。"))}finally{he.value=!1}},wt=async()=>{var e,a,v,s,c,u,T,V;const t=r(i.value);if(!t){o.warning("请先准备当前幕正文，再生成优化版本。");return}if(!_.value){o.warning("请先点击“一键生成AI优化建议”，确认当前幕优化方向后再生成优化版本。");return}ye.value=!0,E.value=null;try{const R=_.value;if(!R)throw new Error("当前幕优化建议结果为空");const p=await Ft(t,l.pipelineOutline||"",l.pipelineCharacters||"",l.pipelineRequirements||"",R,O.value);if(_.value=((e=p==null?void 0:p.data)==null?void 0:e.analysis)||R,((a=p==null?void 0:p.data)==null?void 0:a.generated)===!1){E.value=null,l.pipelineLatestActReviewed=!0,o.success("当前幕暂时不需要生成优化版本。");return}const ae=r(((v=p==null?void 0:p.data)==null?void 0:v.revised_act)||""),le=r(((s=p==null?void 0:p.data)==null?void 0:s.revised_content)||"");if(!ae||!le)throw new Error("AI 没有返回可应用的优化版本");E.value={revisedAct:ae,revisedContent:le,sourceText:t,completion:((c=p==null?void 0:p.data)==null?void 0:c.completion)||null,warning:((u=p==null?void 0:p.data)==null?void 0:u.warning)||"",acceptedWithIssues:!!((T=p==null?void 0:p.data)!=null&&T.accepted_with_issues),generated:!!((V=p==null?void 0:p.data)!=null&&V.generated)},o.success(E.value.acceptedWithIssues?"AI 优化版本已生成，你可以先查看下面的版本，再决定是否替换当前正文。":"AI 优化版本已生成，确认后可直接应用。")}catch(R){console.error(R),o.warning(me(R,"当前幕优化版本生成失败，请稍后重试。"))}finally{ye.value=!1}},Ct=async()=>{var t;if((t=E.value)!=null&&t.revisedContent){if(r(i.value)!==E.value.sourceText){o.warning("当前幕正文已经变化，请重新生成优化版本，避免覆盖你刚刚的新改动。");return}we.value=!0;try{const e=E.value;if(!e)return;D(e.revisedContent),$(e.revisedContent,{preserveWhitespace:!0,source:"external"}),l.pipelineLatestActReviewed=!e.acceptedWithIssues,ne(e.completion||N.value||null),be(),o.success(l.pipelineLatestActReviewed&&z.value?ke.value:"AI 优化版本已应用到当前幕。")}catch(e){console.error(e),o.warning("应用 AI 优化版本失败，请稍后重试。")}finally{we.value=!1}}},kt=async()=>{var e,a,v,s,c;const t=r(i.value);if(!t){o.warning("请先准备剧本文本，再生成下一幕。");return}if(z.value){o.info(ce.value);return}if(oe.value&&!G.value){o.info(`当前正在生成${l.pipelineGenerationTargetAct||Z.value||"下一幕"}，请稍等。`);return}G.value=!0,l.pipelineGenerationInFlight=!0,l.pipelineGenerationTargetAct=Z.value||"下一幕",be();try{const u=await Pt(t,l.pipelineOutline||"",l.pipelineCharacters||"",l.pipelineRequirements||"",O.value),T=r(((e=u.data)==null?void 0:e.text)||"");if(!T){ne(((a=u.data)==null?void 0:a.completion)||N.value||null),o.info(ce.value);return}const V=r(`${t}

${T}`,!1);D(V),$(V,{preserveWhitespace:!0,source:"external"}),T&&(l.pipelineLatestActReviewed=!1);const R=T?i.value:t;ne(((v=u.data)==null?void 0:v.completion)||null),(s=u.data)!=null&&s.data?Ae(u.data.data):await Te(R),(c=u.data)!=null&&c.accepted_with_issues&&T?o.warning("下一幕已生成，但当前幕还有可继续优化的细节。可以先生成 AI 优化建议，再决定是否生成优化版本。"):z.value?o.success(ce.value):T?o.success(`下一幕已生成，当前状态：${Ce.value}。`):o.warning("本次没有生成新的幕内容，请稍后重试。")}catch(u){console.error(u),o.warning(me(u,"生成下一幕失败，请稍后重试。"))}finally{G.value=!1,l.pipelineGenerationInFlight=!1,l.pipelineGenerationTargetAct=""}},Re=()=>{qe({title:Ie(),content:r(i.value)})||o.warning("请先准备剧本文本，并允许浏览器弹出导出窗口。")},bt=async()=>{const t=r(i.value);if(!t){o.warning("请先准备完整剧本文本，再检测叙事指纹。");return}l.scriptContent=t;try{await m.push({name:"Fingerprint",query:{autorun:"1"}})}catch(e){console.error(e);const a="/ai-screenplay-system/";window.location.href=`${a}#/fingerprint?autorun=1`}},_t=t=>{if(!(typeof window>"u"||typeof window.saveManually!="function"))try{window.saveManually(t)}catch(e){console.error(e)}},St=async()=>{var s;const t=r(i.value);if(!t){o.warning("请先准备当前集剧本文本，再继续生成下一集。");return}if(!qe({title:Ie(t),content:t})){o.warning("请先准备剧本文本，并允许浏览器弹出导出窗口。");return}X.value=!0,_t("电视剧当前集导出后进入下一集");let a={previousEnding:t,characterFocus:"",toneDirection:"",cliffhanger:""};try{const c=await qt(t),u=((s=c==null?void 0:c.data)==null?void 0:s.fields)||{};a={previousEnding:r(u.previous_ending||t),characterFocus:r(u.character_focus||""),toneDirection:r(u.tone_direction||""),cliffhanger:r(u.cliffhanger||"")}}catch(c){console.error(c),o.warning("下一集预填建议生成失败，先保留上一集承接内容；你仍可手动调整其余字段。")}if(!Nt(a)){X.value=!1,o.warning("当前集 PDF 导出窗口已打开，但暂时无法自动带入下一集信息，请稍后重试。");return}try{await m.push({name:"Pipeline"})}catch(c){console.error(c);const u="/ai-screenplay-system/";window.location.href=`${u}#/`;return}finally{X.value=!1}},We=()=>{I&&I.resize()};return pe(()=>i.value,t=>{const e=r(t);l.scriptContent=e,Y.value==="rich"?j():Y.value!=="init"&&D(e),mt(e),(!re.value||Y.value!=="rich")&&ue(),Y.value=""}),pe(()=>l.scriptContent,t=>{const e=r(t||"",!1);e!==r(i.value,!1)&&(D(e),$(e,{preserveWhitespace:!0,source:"external"}))}),pe(()=>l.pipelineCompletionSnapshot,t=>{N.value=t?{...t}:null}),pe(Q,t=>{t&&He()}),At(async()=>{P.value?l.editorRichContent=P.value:D(i.value),l.scriptContent=r(i.value),ne(l.pipelineCompletionSnapshot||null),await gt(),He(),await ve(),ue(),window.addEventListener("resize",We)}),Tt(()=>{te&&clearTimeout(te),window.removeEventListener("resize",We),I&&(I.dispose(),I=null)}),(t,e)=>{var u,T,V,R,p,ae,le;const a=fe("el-button"),v=fe("el-empty"),s=fe("el-tag"),c=fe("el-dialog");return y(),x("div",Qt,[n("section",Xt,[e[9]||(e[9]=n("div",null,[n("p",{class:"kicker"},"Visible Writing Track"),n("h1",null,"显性创作轨"),n("p",{class:"hero-copy"},"在这里继续修改和完善当前剧本。你可以按幕续写、查看优化建议、恢复历史版本，也可以直接导出当前成稿。")],-1)),n("div",Zt,[n("span",en,k(Ze.value),1),w(a,{type:"primary",loading:G.value,disabled:!Qe.value,title:"根据当前剧本文本继续生成下一幕",onClick:kt},{default:f(()=>[g(k(Xe.value),1)]),_:1},8,["loading","disabled"]),w(a,{plain:"",disabled:!r(i.value),title:"基于当前完整剧本文本生成叙事指纹报告",onClick:bt},{default:f(()=>[...e[7]||(e[7]=[g("叙事指纹检测",-1)])]),_:1},8,["disabled"]),Pe.value?H("",!0):(y(),se(a,{key:0,plain:"",title:"导出当前剧本文本为 PDF",onClick:Re},{default:f(()=>[...e[8]||(e[8]=[g("导出 PDF",-1)])]),_:1})),w(a,{plain:"",title:"查看并恢复历史自动存档版本",onClick:e[0]||(e[0]=h=>Q.value=!0)},{default:f(()=>[g("时光机（"+k(J.value.length)+"）",1)]),_:1})])]),n("section",tn,[n("article",nn,[e[10]||(e[10]=n("span",null,"文本长度",-1)),n("strong",null,k(Fe.value.characters),1)]),n("article",an,[e[11]||(e[11]=n("span",null,"段落数量",-1)),n("strong",null,k(Fe.value.paragraphs),1)]),n("article",ln,[e[12]||(e[12]=n("span",null,"剧本状态",-1)),n("strong",null,k(Ce.value),1)])]),z.value?(y(),x("section",sn,[n("div",null,[n("strong",null,k(q.value?"剧本已到达当前收口点":"当前题材已生成到最后一幕"),1),n("p",null,k(ce.value),1)]),Pe.value?(y(),x("div",rn,[w(a,{plain:"",loading:X.value,title:"导出当前集 PDF，并自动进入下一集创作",onClick:St},{default:f(()=>[...e[13]||(e[13]=[g("生成下一集并生成当前集 PDF",-1)])]),_:1},8,["loading"]),w(a,{type:"success",plain:"",disabled:X.value,title:"当前为最后一集，仅导出本集 PDF",onClick:Re},{default:f(()=>[...e[14]||(e[14]=[g("当前是最后一集生成 PDF",-1)])]),_:1},8,["disabled"])])):(y(),se(a,{key:1,type:"success",plain:"",title:"导出当前剧本文本为 PDF",onClick:Re},{default:f(()=>[...e[15]||(e[15]=[g("导出 PDF",-1)])]),_:1}))])):H("",!0),n("div",on,[n("div",cn,[n("section",un,[n("header",dn,[e[16]||(e[16]=n("div",null,[n("p",{class:"kicker dark"},"Visible Track"),n("h2",null,"显性创作轨")],-1)),n("span",pn,k(et.value),1)]),n("div",vn,[n("div",fn,[w(a,{size:"small",type:F.value==="rich"?"primary":"default",onClick:e[1]||(e[1]=h=>Ve("rich"))},{default:f(()=>[...e[17]||(e[17]=[g("可视化排版",-1)])]),_:1},8,["type"]),w(a,{size:"small",type:F.value==="plain"?"primary":"default",onClick:e[2]||(e[2]=h=>Ve("plain"))},{default:f(()=>[...e[18]||(e[18]=[g("纯文本模式",-1)])]),_:1},8,["type"]),w(a,{size:"small",plain:"",onClick:it},{default:f(()=>[...e[19]||(e[19]=[g("强调",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:rt},{default:f(()=>[...e[20]||(e[20]=[g("高亮",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:ot},{default:f(()=>[...e[21]||(e[21]=[g("清除标记",-1)])]),_:1})]),n("div",mn,[w(a,{size:"small",plain:"",onClick:ut},{default:f(()=>[...e[22]||(e[22]=[g("插入幕节",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:dt},{default:f(()=>[...e[23]||(e[23]=[g("插入场次",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:e[3]||(e[3]=h=>Be("内景"))},{default:f(()=>[...e[24]||(e[24]=[g("插入内景",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:e[4]||(e[4]=h=>Be("外景"))},{default:f(()=>[...e[25]||(e[25]=[g("插入外景",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:pt},{default:f(()=>[...e[26]||(e[26]=[g("插入对白",-1)])]),_:1}),w(a,{size:"small",plain:"",onClick:vt},{default:f(()=>[...e[27]||(e[27]=[g("整理格式",-1)])]),_:1})])]),Ge(n("div",gn,[e[28]||(e[28]=n("div",{class:"rich-shell-head"},[n("span",null,"排版视图"),n("p",null,"当前内容会按剧本结构展示，方便你直接阅读和修改。")],-1)),n("div",{ref_key:"richEditorRef",ref:d,class:"rich-editor",contenteditable:"true",spellcheck:"false",onFocus:lt,onBlur:st,onInput:at},null,544)],512),[[Oe,F.value==="rich"]]),Ge(n("textarea",{ref_key:"plainTextareaRef",ref:A,"onUpdate:modelValue":e[5]||(e[5]=h=>i.value=h),class:"editor-textarea",spellcheck:"false",placeholder:"这里是剧本文本正文，支持正常左键选字、滚轮滚动和直接编辑。"},null,512),[[Oe,F.value==="plain"],[Rt,i.value]])]),n("section",hn,[n("header",yn,[e[32]||(e[32]=n("div",null,[n("p",{class:"kicker muted"},"AI Notes"),n("h2",null,"当前幕 AI 优化建议")],-1)),n("div",wn,[w(a,{size:"small",loading:he.value,title:"分析当前幕里还能补强什么、哪些句子或段落还能改得更好",onClick:yt},{default:f(()=>[...e[29]||(e[29]=[g("一键生成AI优化建议",-1)])]),_:1},8,["loading"]),(u=_.value)!=null&&u.has_issues&&!E.value?(y(),se(a,{key:0,size:"small",type:"warning",loading:ye.value,title:"基于当前优化建议生成新的优化版本",onClick:wt},{default:f(()=>[...e[30]||(e[30]=[g(" 一键生成优化版本 ",-1)])]),_:1},8,["loading"])):H("",!0),E.value?(y(),se(a,{key:1,size:"small",type:"success",loading:we.value,title:"将 AI 优化版本直接应用到当前幕正文",onClick:Ct},{default:f(()=>[...e[31]||(e[31]=[g(" 一键应用优化 ",-1)])]),_:1},8,["loading"])):H("",!0)])]),n("div",Cn,[_.value?(y(),x("div",kn,[n("article",bn,[e[33]||(e[33]=n("div",{class:"review-card-head"},[n("span",null,"建议 1"),n("strong",null,"当前幕还可以补强什么")],-1)),n("p",_n,k((T=_.value.enhancement)==null?void 0:T.summary),1),(y(!0),x(Ee,null,Ne(((V=_.value.enhancement)==null?void 0:V.items)||[],(h,M)=>(y(),x("div",{key:`editor-missing-${M}`,class:"review-row"},[n("strong",null,"补强建议 "+k(M+1),1),n("p",null,k(h.text),1)]))),128)),(((R=_.value.enhancement)==null?void 0:R.items)||[]).length?H("",!0):(y(),x("p",Sn," 这一方面暂时没有明显补强点。 "))]),n("article",xn,[e[34]||(e[34]=n("div",{class:"review-card-head"},[n("span",null,"建议 2"),n("strong",null,"哪些句子或段落还可以改得更好")],-1)),n("p",An,k((p=_.value.polish)==null?void 0:p.summary),1),(y(!0),x(Ee,null,Ne(((ae=_.value.polish)==null?void 0:ae.items)||[],(h,M)=>(y(),x("div",{key:`editor-off-outline-${M}`,class:"review-row"},[n("strong",null,k(h.problem),1),n("p",null,k(h.reason),1),h.snippet?(y(),x("pre",Tn,k(h.snippet),1)):H("",!0)]))),128)),(((le=_.value.polish)==null?void 0:le.items)||[]).length?H("",!0):(y(),x("p",Rn," 这一方面暂时没有明显可优化句段。 "))])])):H("",!0),E.value?(y(),x("section",En,[e[35]||(e[35]=n("div",{class:"revision-box-head"},[n("div",null,[n("p",{class:"kicker muted"},"AI Polish"),n("h3",null,"当前幕优化版本")]),n("span",{class:"pill"}," 可直接应用 ")],-1)),n("textarea",{value:E.value.revisedAct,class:"revision-textarea",readonly:""},null,8,Nn)])):_.value?H("",!0):(y(),x("div",zn))])])]),n("section",$n,[e[36]||(e[36]=Et('<header class="card-head" data-v-e6be00d6><div data-v-e6be00d6><p class="kicker dark" data-v-e6be00d6>Hidden Planning Track</p><h2 data-v-e6be00d6>隐性规划轨</h2></div><span class="pill blue" data-v-e6be00d6>叙事状态网络</span></header><div class="legend" data-v-e6be00d6><span data-v-e6be00d6><i class="dot character" data-v-e6be00d6></i>角色</span><span data-v-e6be00d6><i class="dot scene" data-v-e6be00d6></i>场景</span><span data-v-e6be00d6><i class="dot foreshadow" data-v-e6be00d6></i>伏笔</span></div>',2)),n("div",{ref_key:"chartRef",ref:S,class:"chart"},null,512)])]),w(c,{modelValue:Q.value,"onUpdate:modelValue":e[6]||(e[6]=h=>Q.value=h),title:"时光机 - 版本历史",width:"720px","close-on-click-modal":!1},{default:f(()=>[J.value.length?(y(),x("div",In,[(y(!0),x(Ee,null,Ne(J.value,(h,M)=>(y(),x("article",{key:h.id,class:zt(["version-card",{latest:M===0}])},[n("div",Ln,[n("div",Fn,[w(s,{size:"small",type:M===0?"success":"info"},{default:f(()=>[g(k(M===0?"最新版本":`#${J.value.length-M}`),1)]),_:2},1032,["type"]),n("strong",null,k(h.savedAtReadable),1)]),w(a,{size:"small",type:"primary",plain:"",loading:ge.value===h.id,title:"用该历史版本覆盖当前内容",onClick:Bn=>ht(h)},{default:f(()=>[...e[37]||(e[37]=[g("恢复到此版本",-1)])]),_:1},8,["loading","onClick"])]),n("pre",Pn,k(ft(h)),1)],2))),128))])):(y(),se(v,{key:0,description:"还没有可恢复的自动存档。"}))]),_:1},8,["modelValue"])])}}},qn=Dt(Vn,[["__scopeId","data-v-e6be00d6"]]);export{qn as default};
