(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))i(a);new MutationObserver(a=>{for(const r of a)if(r.type==="childList")for(const n of r.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&i(n)}).observe(document,{childList:!0,subtree:!0});function s(a){const r={};return a.integrity&&(r.integrity=a.integrity),a.referrerPolicy&&(r.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?r.credentials="include":a.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function i(a){if(a.ep)return;a.ep=!0;const r=s(a);fetch(a.href,r)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const F=globalThis,K=F.ShadowRoot&&(F.ShadyCSS===void 0||F.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,W=Symbol(),J=new WeakMap;let he=class{constructor(e,s,i){if(this._$cssResult$=!0,i!==W)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=s}get styleSheet(){let e=this.o;const s=this.t;if(K&&e===void 0){const i=s!==void 0&&s.length===1;i&&(e=J.get(s)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&J.set(s,e))}return e}toString(){return this.cssText}};const ye=t=>new he(typeof t=="string"?t:t+"",void 0,W),ve=(t,...e)=>{const s=t.length===1?t[0]:e.reduce((i,a,r)=>i+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(a)+t[r+1],t[0]);return new he(s,t,W)},be=(t,e)=>{if(K)t.adoptedStyleSheets=e.map(s=>s instanceof CSSStyleSheet?s:s.styleSheet);else for(const s of e){const i=document.createElement("style"),a=F.litNonce;a!==void 0&&i.setAttribute("nonce",a),i.textContent=s.cssText,t.appendChild(i)}},Z=K?t=>t:t=>t instanceof CSSStyleSheet?(e=>{let s="";for(const i of e.cssRules)s+=i.cssText;return ye(s)})(t):t;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:$e,defineProperty:ke,getOwnPropertyDescriptor:we,getOwnPropertyNames:Se,getOwnPropertySymbols:_e,getPrototypeOf:Ce}=Object,k=globalThis,X=k.trustedTypes,Ae=X?X.emptyScript:"",z=k.reactiveElementPolyfillSupport,D=(t,e)=>t,G={toAttribute(t,e){switch(e){case Boolean:t=t?Ae:null;break;case Object:case Array:t=t==null?t:JSON.stringify(t)}return t},fromAttribute(t,e){let s=t;switch(e){case Boolean:s=t!==null;break;case Number:s=t===null?null:Number(t);break;case Object:case Array:try{s=JSON.parse(t)}catch{s=null}}return s}},Y=(t,e)=>!$e(t,e),ee={attribute:!0,type:String,converter:G,reflect:!1,useDefault:!1,hasChanged:Y};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),k.litPropertyMetadata??(k.litPropertyMetadata=new WeakMap);let A=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,s=ee){if(s.state&&(s.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((s=Object.create(s)).wrapped=!0),this.elementProperties.set(e,s),!s.noAccessor){const i=Symbol(),a=this.getPropertyDescriptor(e,i,s);a!==void 0&&ke(this.prototype,e,a)}}static getPropertyDescriptor(e,s,i){const{get:a,set:r}=we(this.prototype,e)??{get(){return this[s]},set(n){this[s]=n}};return{get:a,set(n){const p=a==null?void 0:a.call(this);r==null||r.call(this,n),this.requestUpdate(e,p,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ee}static _$Ei(){if(this.hasOwnProperty(D("elementProperties")))return;const e=Ce(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(D("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(D("properties"))){const s=this.properties,i=[...Se(s),..._e(s)];for(const a of i)this.createProperty(a,s[a])}const e=this[Symbol.metadata];if(e!==null){const s=litPropertyMetadata.get(e);if(s!==void 0)for(const[i,a]of s)this.elementProperties.set(i,a)}this._$Eh=new Map;for(const[s,i]of this.elementProperties){const a=this._$Eu(s,i);a!==void 0&&this._$Eh.set(a,s)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const s=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const a of i)s.unshift(Z(a))}else e!==void 0&&s.push(Z(e));return s}static _$Eu(e,s){const i=s.attribute;return i===!1?void 0:typeof i=="string"?i:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(s=>this.enableUpdating=s),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(s=>s(this))}addController(e){var s;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((s=e.hostConnected)==null||s.call(e))}removeController(e){var s;(s=this._$EO)==null||s.delete(e)}_$E_(){const e=new Map,s=this.constructor.elementProperties;for(const i of s.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return be(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(s=>{var i;return(i=s.hostConnected)==null?void 0:i.call(s)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(s=>{var i;return(i=s.hostDisconnected)==null?void 0:i.call(s)})}attributeChangedCallback(e,s,i){this._$AK(e,i)}_$ET(e,s){var r;const i=this.constructor.elementProperties.get(e),a=this.constructor._$Eu(e,i);if(a!==void 0&&i.reflect===!0){const n=(((r=i.converter)==null?void 0:r.toAttribute)!==void 0?i.converter:G).toAttribute(s,i.type);this._$Em=e,n==null?this.removeAttribute(a):this.setAttribute(a,n),this._$Em=null}}_$AK(e,s){var r,n;const i=this.constructor,a=i._$Eh.get(e);if(a!==void 0&&this._$Em!==a){const p=i.getPropertyOptions(a),c=typeof p.converter=="function"?{fromAttribute:p.converter}:((r=p.converter)==null?void 0:r.fromAttribute)!==void 0?p.converter:G;this._$Em=a;const g=c.fromAttribute(s,p.type);this[a]=g??((n=this._$Ej)==null?void 0:n.get(a))??g,this._$Em=null}}requestUpdate(e,s,i,a=!1,r){var n;if(e!==void 0){const p=this.constructor;if(a===!1&&(r=this[e]),i??(i=p.getPropertyOptions(e)),!((i.hasChanged??Y)(r,s)||i.useDefault&&i.reflect&&r===((n=this._$Ej)==null?void 0:n.get(e))&&!this.hasAttribute(p._$Eu(e,i))))return;this.C(e,s,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,s,{useDefault:i,reflect:a,wrapped:r},n){i&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,n??s??this[e]),r!==!0||n!==void 0)||(this._$AL.has(e)||(this.hasUpdated||i||(s=void 0),this._$AL.set(e,s)),a===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(s){Promise.reject(s)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var i;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[r,n]of this._$Ep)this[r]=n;this._$Ep=void 0}const a=this.constructor.elementProperties;if(a.size>0)for(const[r,n]of a){const{wrapped:p}=n,c=this[r];p!==!0||this._$AL.has(r)||c===void 0||this.C(r,void 0,n,c)}}let e=!1;const s=this._$AL;try{e=this.shouldUpdate(s),e?(this.willUpdate(s),(i=this._$EO)==null||i.forEach(a=>{var r;return(r=a.hostUpdate)==null?void 0:r.call(a)}),this.update(s)):this._$EM()}catch(a){throw e=!1,this._$EM(),a}e&&this._$AE(s)}willUpdate(e){}_$AE(e){var s;(s=this._$EO)==null||s.forEach(i=>{var a;return(a=i.hostUpdated)==null?void 0:a.call(i)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(s=>this._$ET(s,this[s]))),this._$EM()}updated(e){}firstUpdated(e){}};A.elementStyles=[],A.shadowRootOptions={mode:"open"},A[D("elementProperties")]=new Map,A[D("finalized")]=new Map,z==null||z({ReactiveElement:A}),(k.reactiveElementVersions??(k.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const O=globalThis,te=t=>t,j=O.trustedTypes,se=j?j.createPolicy("lit-html",{createHTML:t=>t}):void 0,ue="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,pe="?"+$,xe=`<${pe}>`,C=document,T=()=>C.createComment(""),P=t=>t===null||typeof t!="object"&&typeof t!="function",Q=Array.isArray,Ee=t=>Q(t)||typeof(t==null?void 0:t[Symbol.iterator])=="function",H=`[ 	
\f\r]`,M=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ie=/-->/g,ae=/>/g,w=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),re=/'/g,ne=/"/g,ge=/^(?:script|style|textarea|title)$/i,Me=t=>(e,...s)=>({_$litType$:t,strings:e,values:s}),o=Me(1),x=Symbol.for("lit-noChange"),u=Symbol.for("lit-nothing"),oe=new WeakMap,S=C.createTreeWalker(C,129);function fe(t,e){if(!Q(t)||!t.hasOwnProperty("raw"))throw Error("invalid template strings array");return se!==void 0?se.createHTML(e):e}const De=(t,e)=>{const s=t.length-1,i=[];let a,r=e===2?"<svg>":e===3?"<math>":"",n=M;for(let p=0;p<s;p++){const c=t[p];let g,y,f=-1,v=0;for(;v<c.length&&(n.lastIndex=v,y=n.exec(c),y!==null);)v=n.lastIndex,n===M?y[1]==="!--"?n=ie:y[1]!==void 0?n=ae:y[2]!==void 0?(ge.test(y[2])&&(a=RegExp("</"+y[2],"g")),n=w):y[3]!==void 0&&(n=w):n===w?y[0]===">"?(n=a??M,f=-1):y[1]===void 0?f=-2:(f=n.lastIndex-y[2].length,g=y[1],n=y[3]===void 0?w:y[3]==='"'?ne:re):n===ne||n===re?n=w:n===ie||n===ae?n=M:(n=w,a=void 0);const b=n===w&&t[p+1].startsWith("/>")?" ":"";r+=n===M?c+xe:f>=0?(i.push(g),c.slice(0,f)+ue+c.slice(f)+$+b):c+$+(f===-2?p:b)}return[fe(t,r+(t[s]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),i]};class I{constructor({strings:e,_$litType$:s},i){let a;this.parts=[];let r=0,n=0;const p=e.length-1,c=this.parts,[g,y]=De(e,s);if(this.el=I.createElement(g,i),S.currentNode=this.el.content,s===2||s===3){const f=this.el.content.firstChild;f.replaceWith(...f.childNodes)}for(;(a=S.nextNode())!==null&&c.length<p;){if(a.nodeType===1){if(a.hasAttributes())for(const f of a.getAttributeNames())if(f.endsWith(ue)){const v=y[n++],b=a.getAttribute(f).split($),U=/([.?@])?(.*)/.exec(v);c.push({type:1,index:r,name:U[2],strings:b,ctor:U[1]==="."?Re:U[1]==="?"?Te:U[1]==="@"?Pe:q}),a.removeAttribute(f)}else f.startsWith($)&&(c.push({type:6,index:r}),a.removeAttribute(f));if(ge.test(a.tagName)){const f=a.textContent.split($),v=f.length-1;if(v>0){a.textContent=j?j.emptyScript:"";for(let b=0;b<v;b++)a.append(f[b],T()),S.nextNode(),c.push({type:2,index:++r});a.append(f[v],T())}}}else if(a.nodeType===8)if(a.data===pe)c.push({type:2,index:r});else{let f=-1;for(;(f=a.data.indexOf($,f+1))!==-1;)c.push({type:7,index:r}),f+=$.length-1}r++}}static createElement(e,s){const i=C.createElement("template");return i.innerHTML=e,i}}function E(t,e,s=t,i){var n,p;if(e===x)return e;let a=i!==void 0?(n=s._$Co)==null?void 0:n[i]:s._$Cl;const r=P(e)?void 0:e._$litDirective$;return(a==null?void 0:a.constructor)!==r&&((p=a==null?void 0:a._$AO)==null||p.call(a,!1),r===void 0?a=void 0:(a=new r(t),a._$AT(t,s,i)),i!==void 0?(s._$Co??(s._$Co=[]))[i]=a:s._$Cl=a),a!==void 0&&(e=E(t,a._$AS(t,e.values),a,i)),e}class Oe{constructor(e,s){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=s}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:s},parts:i}=this._$AD,a=((e==null?void 0:e.creationScope)??C).importNode(s,!0);S.currentNode=a;let r=S.nextNode(),n=0,p=0,c=i[0];for(;c!==void 0;){if(n===c.index){let g;c.type===2?g=new N(r,r.nextSibling,this,e):c.type===1?g=new c.ctor(r,c.name,c.strings,this,e):c.type===6&&(g=new Ie(r,this,e)),this._$AV.push(g),c=i[++p]}n!==(c==null?void 0:c.index)&&(r=S.nextNode(),n++)}return S.currentNode=C,a}p(e){let s=0;for(const i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(e,i,s),s+=i.strings.length-2):i._$AI(e[s])),s++}}class N{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,s,i,a){this.type=2,this._$AH=u,this._$AN=void 0,this._$AA=e,this._$AB=s,this._$AM=i,this.options=a,this._$Cv=(a==null?void 0:a.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const s=this._$AM;return s!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=s.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,s=this){e=E(this,e,s),P(e)?e===u||e==null||e===""?(this._$AH!==u&&this._$AR(),this._$AH=u):e!==this._$AH&&e!==x&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Ee(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==u&&P(this._$AH)?this._$AA.nextSibling.data=e:this.T(C.createTextNode(e)),this._$AH=e}$(e){var r;const{values:s,_$litType$:i}=e,a=typeof i=="number"?this._$AC(e):(i.el===void 0&&(i.el=I.createElement(fe(i.h,i.h[0]),this.options)),i);if(((r=this._$AH)==null?void 0:r._$AD)===a)this._$AH.p(s);else{const n=new Oe(a,this),p=n.u(this.options);n.p(s),this.T(p),this._$AH=n}}_$AC(e){let s=oe.get(e.strings);return s===void 0&&oe.set(e.strings,s=new I(e)),s}k(e){Q(this._$AH)||(this._$AH=[],this._$AR());const s=this._$AH;let i,a=0;for(const r of e)a===s.length?s.push(i=new N(this.O(T()),this.O(T()),this,this.options)):i=s[a],i._$AI(r),a++;a<s.length&&(this._$AR(i&&i._$AB.nextSibling,a),s.length=a)}_$AR(e=this._$AA.nextSibling,s){var i;for((i=this._$AP)==null?void 0:i.call(this,!1,!0,s);e!==this._$AB;){const a=te(e).nextSibling;te(e).remove(),e=a}}setConnected(e){var s;this._$AM===void 0&&(this._$Cv=e,(s=this._$AP)==null||s.call(this,e))}}class q{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,s,i,a,r){this.type=1,this._$AH=u,this._$AN=void 0,this.element=e,this.name=s,this._$AM=a,this.options=r,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=u}_$AI(e,s=this,i,a){const r=this.strings;let n=!1;if(r===void 0)e=E(this,e,s,0),n=!P(e)||e!==this._$AH&&e!==x,n&&(this._$AH=e);else{const p=e;let c,g;for(e=r[0],c=0;c<r.length-1;c++)g=E(this,p[i+c],s,c),g===x&&(g=this._$AH[c]),n||(n=!P(g)||g!==this._$AH[c]),g===u?e=u:e!==u&&(e+=(g??"")+r[c+1]),this._$AH[c]=g}n&&!a&&this.j(e)}j(e){e===u?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class Re extends q{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===u?void 0:e}}class Te extends q{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==u)}}class Pe extends q{constructor(e,s,i,a,r){super(e,s,i,a,r),this.type=5}_$AI(e,s=this){if((e=E(this,e,s,0)??u)===x)return;const i=this._$AH,a=e===u&&i!==u||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,r=e!==u&&(i===u||a);a&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var s;typeof this._$AH=="function"?this._$AH.call(((s=this.options)==null?void 0:s.host)??this.element,e):this._$AH.handleEvent(e)}}class Ie{constructor(e,s,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=s,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){E(this,e)}}const B=O.litHtmlPolyfillSupport;B==null||B(I,N),(O.litHtmlVersions??(O.litHtmlVersions=[])).push("3.3.3");const Le=(t,e,s)=>{const i=(s==null?void 0:s.renderBefore)??e;let a=i._$litPart$;if(a===void 0){const r=(s==null?void 0:s.renderBefore)??null;i._$litPart$=a=new N(e.insertBefore(T(),r),r,void 0,s??{})}return a._$AI(t),a};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const _=globalThis;class R extends A{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var s;const e=super.createRenderRoot();return(s=this.renderOptions).renderBefore??(s.renderBefore=e.firstChild),e}update(e){const s=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Le(s,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return x}}var de;R._$litElement$=!0,R.finalized=!0,(de=_.litElementHydrateSupport)==null||de.call(_,{LitElement:R});const V=_.litElementPolyfillSupport;V==null||V({LitElement:R});(_.litElementVersions??(_.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ne=t=>(e,s)=>{s!==void 0?s.addInitializer(()=>{customElements.define(t,e)}):customElements.define(t,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ue={attribute:!0,type:String,converter:G,reflect:!1,hasChanged:Y},Fe=(t=Ue,e,s)=>{const{kind:i,metadata:a}=s;let r=globalThis.litPropertyMetadata.get(a);if(r===void 0&&globalThis.litPropertyMetadata.set(a,r=new Map),i==="setter"&&((t=Object.create(t)).wrapped=!0),r.set(s.name,t),i==="accessor"){const{name:n}=s;return{set(p){const c=e.get.call(this);e.set.call(this,p),this.requestUpdate(n,c,t,!0,p)},init(p){return p!==void 0&&this.C(n,void 0,t,p),p}}}if(i==="setter"){const{name:n}=s;return function(p){const c=this[n];e.call(this,p),this.requestUpdate(n,c,t,!0,p)}}throw Error("Unsupported decorator location: "+i)};function Ge(t){return(e,s)=>typeof s=="object"?Fe(t,e,s):((i,a,r)=>{const n=a.hasOwnProperty(r);return a.constructor.createProperty(r,i),n?Object.getOwnPropertyDescriptor(a,r):void 0})(t,e,s)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function h(t){return Ge({...t,state:!0,attribute:!1})}class L extends Error{constructor(e,s,i,a,r,n){const p=a||`API request failed with status ${e} (${s})`;super(p),this.name="ApiError",this.status=e,this.statusText=s,this.body=i,this.detail=a,this.pickerToken=r,this.activeToken=n,Object.setPrototypeOf(this,L.prototype)}get isConflict(){return this.status===409}get isNotFound(){return this.status===404}get isUnprocessable(){return this.status===422}get isForbidden(){return this.status===403}get isBadRequest(){return this.status===400}}async function je(t){const e=t.status,s=t.statusText;let i=null,a,r,n;try{if((t.headers.get("content-type")||"").includes("application/json")){const c=await t.json();i=c,typeof c.detail=="string"?a=c.detail:Array.isArray(c.detail)&&c.detail.length>0&&(a=c.detail.map(g=>g.msg||JSON.stringify(g)).join("; ")),typeof c.picker_token=="string"&&(r=c.picker_token),typeof c.active_token=="string"&&(n=c.active_token)}else{const c=await t.text();i=c,a=c||void 0}}catch{}return new L(e,s,i,a,r,n)}class qe{constructor(e={}){this.baseUrl=e.baseUrl?e.baseUrl.replace(/\/+$/,""):"",this._fetch=e.fetch??globalThis.fetch.bind(globalThis)}async request(e,s={}){const i=s.method??"GET",a=i==="GET";let r=`${this.baseUrl}${e.startsWith("/")?e:`/${e}`}`;if(s.params){const g=new URLSearchParams;for(const[f,v]of Object.entries(s.params))v!=null&&g.append(f,String(v));const y=g.toString();y&&(r+=(r.includes("?")?"&":"?")+y)}const n={...s.headers};a||(n["X-Flashcards-Request"]="1");let p;s.body!==void 0&&s.body!==null&&(s.body instanceof FormData||s.body instanceof Blob||s.body instanceof ArrayBuffer||ArrayBuffer.isView(s.body)?p=s.body:(n["Content-Type"]="application/json",p=JSON.stringify(s.body)));const c=await this._fetch(r,{method:i,headers:n,body:p});if(!c.ok)throw await je(c);if(s.responseType==="text")return await c.text();if(s.responseType==="blob")return await c.blob();if(!(c.status===204||c.headers.get("content-length")==="0"))return await c.json()}async lookup(e){return this.request("/vocab/lookup",{method:"GET",params:{q:e}})}async lookupPost(e){return this.request("/vocab/lookup",{method:"POST",body:{query:e}})}async activateDictionary(e){return this.request("/vocab/dictionary/activate",{method:"POST",body:e})}async highlight(e){return this.request("/vocab/highlight",{method:"POST",body:e})}async captureCards(e){return this.request("/vocab/cards",{method:"POST",body:e})}async importCsv(e){return this.request("/vocab/import/csv",{method:"POST",body:e})}async createNote(e){return this.request("/vocab/notes",{method:"POST",body:e})}async getNextCard(e){return this.request("/vocab/cards/next",{method:"GET",params:{deck_id:e}})}async reviewCard(e,s){return this.request(`/vocab/cards/${e}/review`,{method:"POST",body:{confidence:s}})}async setGloss(e,s,i){return this.request(`/vocab/notes/${e}/gloss`,{method:"POST",body:{language:s,meaning_text:i}})}async deleteGloss(e,s){return this.request(`/vocab/notes/${e}/gloss`,{method:"DELETE",params:{language:s}})}async uploadAudio(e,s,i){const a={};return i&&!(s instanceof FormData)&&(a["Content-Type"]=i),this.request(`/vocab/notes/${e}/audio`,{method:"POST",body:s,headers:a})}async revertAudio(e){return this.request(`/vocab/notes/${e}/audio`,{method:"DELETE"})}getAudioUrl(e){const s=encodeURIComponent(String(e));return`${this.baseUrl}/vocab/audio/${s}`}async fetchAudio(e){const s=encodeURIComponent(String(e));return this.request(`/vocab/audio/${s}`,{method:"GET",responseType:"blob"})}async getDecks(){return this.request("/vocab/decks",{method:"GET"})}async createDeck(e){const s={name:e};return this.request("/vocab/decks",{method:"POST",body:s})}async deleteDeck(e){return this.request(`/vocab/decks/${e}`,{method:"DELETE"})}async exportAnki(e){return this.request("/vocab/export/anki",{method:"GET",params:{deck_id:e},responseType:"text"})}async exportApkg(e){return this.request("/vocab/export/apkg",{method:"GET",params:{deck_id:e},responseType:"blob"})}async getDictionarySettings(){return this.request("/vocab/settings/dictionary",{method:"GET"})}async installOffline(e={}){return this.request("/vocab/settings/dictionary/install-offline",{method:"POST",body:e})}async removeOffline(e={}){return this.request("/vocab/settings/dictionary/remove-offline",{method:"POST",body:e})}async clearOnlineCache(){return this.request("/vocab/settings/dictionary/clear-online-cache",{method:"POST",body:{}})}async useOnline(){return this.request("/vocab/settings/dictionary/use-online",{method:"POST",body:{}})}async useOffline(){return this.request("/vocab/settings/dictionary/use-offline",{method:"POST",body:{}})}}function ze(t){return new qe(t)}const me="wortlaut.study.alwaysShowExtraInfo";function He(t){if(!t)return!1;try{return t.getItem(me)==="true"}catch{return!1}}function Be(t,e){if(t)try{t.setItem(me,e?"true":"false")}catch{}}function ce(){return!1}function Ve(t){return t.isRevealed?t.newPreference:!1}var Ke=Object.defineProperty,We=Object.getOwnPropertyDescriptor,d=(t,e,s,i)=>{for(var a=i>1?void 0:i?We(e,s):e,r=t.length-1,n;r>=0;r--)(n=t[r])&&(a=(i?n(e,s,a):n(a))||a);return i&&a&&Ke(e,s,a),a};const Ye=[["1","Not at all"],["2","Barely"],["3","With effort"],["4","Comfortably"],["5","Without doubt"]],m=ze();function le(){try{return window.localStorage}catch{return null}}let l=class extends R{constructor(){super(...arguments),this.decks=[],this.deckStatus="loading",this.errorMessage="",this.successMessage="",this.newDeckName="",this.selectedDeckId=null,this.pendingDeleteDeckId=null,this.isCreating=!1,this.isDeleting=!1,this.lookupQuery="",this.lookupStatus="idle",this.lookupCandidates=[],this.lookupAssetToken="",this.selectedCandidate=null,this.selectedSenseRef=null,this.selectedMeaningLanguages=["de","en"],this.userMeaningDe="",this.userMeaningEn="",this.manualDeckId=null,this.isSavingNote=!1,this.importDeckName="",this.importText="",this.importFileName="",this.isReadingImportFile=!1,this.isImporting=!1,this.exportingFormat=null,this.captureSentence="",this.captureLessonLabel="",this.captureSpanStart=0,this.captureSpanEnd=0,this.captureStatus="idle",this.captureCandidates=[],this.captureAssetToken="",this.captureContext=null,this.captureSelections={},this.captureMeaningLanguages=["de","en"],this.captureUserMeaningDe="",this.captureUserMeaningEn="",this.captureDeckId=null,this.captureError="",this.captureDictionaryChanged=!1,this.isCapturing=!1,this.view="decks",this.studyDeckId=null,this.studyStatus="idle",this.studyCard=null,this.isRevealed=!1,this.isReviewing=!1,this.studyError="",this.extraInfoOpen=!1,this.alwaysShowExtraInfo=He(le()),this.glossDrafts={de:"",en:""},this.glossState="",this.glossError="",this.glossSavingLanguage=null,this.audioStatus="idle",this.audioMessage="",this.recordingStatus="idle",this.recordingBlob=null,this.recordingNoteId=null,this.recordingPreviewUrl="",this.recordingError="",this.showRecordingControls=!1,this.revertConfirmation=!1,this.hasCustomAudio=!1,this.dictionaryMode="unconfigured",this.dictionarySettings=null,this.dictionarySettingsStatus="loading",this.dictionaryAction="idle",this.dictionaryActionMessage="",this.dictionaryActionError="",this.confirmRemoveOffline=!1,this.focusTarget=null,this.audioPlayer=null,this.mediaRecorder=null,this.recordingChunks=[],this.handleStudyKeydown=t=>{if(this.view!=="study")return;const e=t.target;if(!(e!=null&&e.closest('input, textarea, select, [contenteditable="true"]'))){if(t.code==="Space"&&!this.isRevealed){t.preventDefault(),this.revealCard();return}if(t.key>="1"&&t.key<="5"&&this.isRevealed){t.preventDefault(),this.submitConfidence(Number(t.key));return}t.key.toLowerCase()==="r"&&(t.preventDefault(),this.playPronunciation())}}}connectedCallback(){super.connectedCallback(),this.loadDecks(),this.loadDictionarySettings(),window.addEventListener("keydown",this.handleStudyKeydown)}disconnectedCallback(){window.removeEventListener("keydown",this.handleStudyKeydown),this.stopAudio(),this.releaseRecordingPreview(),super.disconnectedCallback()}updated(){if(!this.focusTarget)return;const t=this.focusTarget==="answer"?"[data-study-answer]":"[data-study-empty]",e=this.renderRoot.querySelector(t);e&&(e.focus(),this.focusTarget=null)}async loadDecks(){this.deckStatus="loading",this.errorMessage="",this.successMessage="";try{const t=await m.getDecks();return this.decks=t,this.selectedDeckId!==null&&!t.some(e=>e.id===this.selectedDeckId)&&(this.selectedDeckId=null),this.manualDeckId!==null&&!t.some(e=>e.id===this.manualDeckId)&&(this.manualDeckId=null),this.captureDeckId!==null&&!t.some(e=>e.id===this.captureDeckId)&&(this.captureDeckId=null),this.deckStatus="ready",t}catch(t){return this.deckStatus="error",this.errorMessage=this.messageFor(t,"Decks could not be loaded."),null}}async createDeck(t){t.preventDefault();const e=this.newDeckName.trim();if(!e){this.successMessage="",this.errorMessage="Enter a deck name before creating it.";return}this.isCreating=!0,this.errorMessage="",this.successMessage="";try{const s=await m.createDeck(e);this.newDeckName="";const i=await this.loadDecks();if(i===null){this.errorMessage=`“${s.name}” may have been created, but the deck list could not be refreshed.`;return}const a=i.find(r=>r.id===s.id);if(!a){this.errorMessage=`The server did not return “${s.name}” after creation. It was not opened.`;return}this.selectedDeckId=a.id,this.manualDeckId=a.id,this.captureDeckId=a.id,this.importDeckName=a.name,this.successMessage=`Created and opened “${a.name}”.`}catch(s){this.successMessage="",this.errorMessage=this.messageFor(s,"Deck could not be created.")}finally{this.isCreating=!1}}async deleteDeck(t){this.isDeleting=!0,this.errorMessage="",this.successMessage="";try{if(!(await m.deleteDeck(t.id)).deleted)throw new Error("The server did not confirm deletion.");this.pendingDeleteDeckId=null;const s=await this.loadDecks();if(s===null){this.errorMessage=`“${t.name}” may have been deleted, but the deck list could not be refreshed.`;return}if(s.some(i=>i.id===t.id)){this.errorMessage=`The server still returned “${t.name}” after deletion. The deletion was not confirmed.`;return}this.selectedDeckId===t.id&&(this.selectedDeckId=null),this.successMessage=`Deleted “${t.name}”. Notes with review history were preserved by the server.`}catch(e){this.successMessage="",this.errorMessage=this.messageFor(e,"Deck could not be deleted.")}finally{this.isDeleting=!1}}messageFor(t,e){return t instanceof L&&t.detail?t.detail:t instanceof Error&&t.message?t.message:e}openDeck(t){this.selectedDeckId=t.id,this.manualDeckId=t.id,this.captureDeckId=t.id,this.importDeckName=t.name,this.view="deck",this.successMessage=""}async openStudy(t){if(this.recordingBlob||this.recordingStatus==="recording"){this.view="study",this.errorMessage="Save or discard the local recording before changing study sessions.";return}this.view="study",this.studyDeckId=t??null,this.studyCard=null,this.isRevealed=!1,this.extraInfoOpen=ce(),this.studyError="",this.clearPronunciationState(),await this.loadStudyCard()}clearPronunciationState(){this.stopAudio(),this.audioMessage="",this.audioStatus="idle",this.showRecordingControls=!1,this.revertConfirmation=!1}async loadStudyCard(){var t,e;this.studyStatus="loading",this.studyError="";try{const s=await m.getNextCard(this.studyDeckId??void 0);this.studyCard=s.card,this.isRevealed=!1,this.extraInfoOpen=ce(),this.hasCustomAudio=!!((e=(t=s.card)==null?void 0:t.front.audio_trigger.token)!=null&&e.startsWith("custom:")),this.glossDrafts={de:this.userGlossValue(s.card,"de"),en:this.userGlossValue(s.card,"en")},this.glossState="",this.glossError="",this.studyStatus=s.card?"ready":"empty",s.card||(this.focusTarget="empty")}catch(s){this.studyCard=null,this.studyStatus="error",this.studyError=this.messageFor(s,"The next card could not be loaded.")}}revealCard(){!this.studyCard||this.isRevealed||this.isReviewing||(this.isRevealed=!0,this.extraInfoOpen=this.alwaysShowExtraInfo,this.focusTarget="answer")}toggleExtraInfo(){this.extraInfoOpen=!this.extraInfoOpen}setAlwaysShowExtraInfo(t){this.alwaysShowExtraInfo=t,Be(le(),t),this.extraInfoOpen=Ve({isRevealed:this.isRevealed,newPreference:t})}async submitConfidence(t){const e=this.studyCard;if(!(!e||!this.isRevealed||this.isReviewing)){if(this.recordingBlob){this.studyError="Save or discard the local recording before continuing to the next card.";return}this.isReviewing=!0,this.studyError="";try{await m.reviewCard(e.card_id,t),await this.loadStudyCard()}catch(s){this.studyError=this.messageFor(s,"Your confidence could not be saved. Try the same rating again.")}finally{this.isReviewing=!1}}}meaningFor(t,e){return t==null?void 0:t.back.meanings.find(s=>s.language===e)}userGlossValue(t,e){const s=this.meaningFor(t,e);return s!=null&&s.is_user_authored?s.lines.join(" "):""}async saveGloss(t){const e=this.studyCard,s=this.glossDrafts[t].trim();if(!(!e||!s)){this.glossSavingLanguage=t,this.glossError="",this.glossState="";try{const i=await m.setGloss(e.note_id,t,s);this.glossDrafts={...this.glossDrafts,[t]:i.meaning_text},this.glossState=`${t==="de"?"German":"English"} meaning saved.`,await this.refreshStudyFace(e.card_id)}catch(i){this.glossError=this.messageFor(i,"That meaning could not be saved.")}finally{this.glossSavingLanguage=null}}}async deleteGloss(t){const e=this.studyCard;if(e){this.glossSavingLanguage=t,this.glossError="",this.glossState="";try{if(!(await m.deleteGloss(e.note_id,t)).deleted)throw new Error("The server did not confirm removal.");this.glossDrafts={...this.glossDrafts,[t]:""},this.glossState=`${t==="de"?"German":"English"} meaning removed.`,await this.refreshStudyFace(e.card_id)}catch(s){this.glossError=this.messageFor(s,"That meaning could not be removed.")}finally{this.glossSavingLanguage=null}}}async refreshStudyFace(t){var e,s;try{const i=await m.getNextCard(this.studyDeckId??void 0);((e=i.card)==null?void 0:e.card_id)===t&&(this.studyCard=i.card,this.hasCustomAudio=!!((s=i.card.front.audio_trigger.token)!=null&&s.startsWith("custom:")))}catch{}}audioRequestId(t){return this.hasCustomAudio?t.note_id:t.front.audio_trigger.lemma}stopAudio(){this.audioPlayer&&(this.audioPlayer.pause(),this.audioPlayer.src="",this.audioPlayer=null),this.audioStatus==="playing"&&(this.audioStatus="idle")}async playPronunciation(){const t=this.studyCard;if(!(!t||!t.front.audio_trigger.available||this.audioStatus==="loading")){this.stopAudio(),this.audioStatus="loading",this.audioMessage="Loading pronunciation…";try{const e=await m.fetchAudio(this.audioRequestId(t)),s=URL.createObjectURL(e),i=new Audio(s);this.audioPlayer=i,i.onended=()=>{URL.revokeObjectURL(s),this.audioPlayer=null,this.audioStatus="idle",this.audioMessage=""},await i.play(),this.audioStatus="playing",this.audioMessage="Playing pronunciation…"}catch(e){this.audioStatus="unavailable",this.audioMessage=this.messageFor(e,"Pronunciation is unavailable right now.")}}}releaseRecordingPreview(){this.recordingPreviewUrl&&URL.revokeObjectURL(this.recordingPreviewUrl),this.recordingPreviewUrl=""}setLocalRecording(t){var e;this.releaseRecordingPreview(),this.recordingBlob=t,this.recordingNoteId=((e=this.studyCard)==null?void 0:e.note_id)??null,this.recordingPreviewUrl=URL.createObjectURL(t),this.recordingStatus="ready",this.recordingError=""}async startRecording(){var t;if(!((t=navigator.mediaDevices)!=null&&t.getUserMedia)||typeof MediaRecorder>"u"){this.recordingError="Recording is not available in this browser. You can choose an audio file instead.";return}try{const e=await navigator.mediaDevices.getUserMedia({audio:!0}),s=new MediaRecorder(e);this.recordingChunks=[],s.ondataavailable=i=>{i.data.size&&this.recordingChunks.push(i.data)},s.onstop=()=>{e.getTracks().forEach(i=>i.stop()),this.setLocalRecording(new Blob(this.recordingChunks,{type:s.mimeType||"audio/webm"}))},s.start(),this.mediaRecorder=s,this.recordingStatus="recording",this.recordingError=""}catch(e){this.recordingError=this.messageFor(e,"Microphone access was not granted. You can choose an audio file instead.")}}stopRecording(){var t;((t=this.mediaRecorder)==null?void 0:t.state)==="recording"&&this.mediaRecorder.stop(),this.mediaRecorder=null}selectAudioFile(t){var s;const e=(s=t.target.files)==null?void 0:s[0];e&&this.setLocalRecording(e)}discardRecording(){this.releaseRecordingPreview(),this.recordingBlob=null,this.recordingNoteId=null,this.recordingStatus="idle",this.recordingError=""}async saveRecording(){const t=this.studyCard,e=this.recordingBlob;if(!(!t||!e||this.recordingNoteId!==t.note_id)){this.recordingStatus="saving",this.recordingError="";try{await m.uploadAudio(t.note_id,e,e.type||"audio/webm"),this.discardRecording(),this.showRecordingControls=!1,this.hasCustomAudio=!0,this.audioMessage="Custom pronunciation saved.",await this.refreshStudyFace(t.card_id)}catch(s){this.recordingStatus="save-error",this.recordingError=this.messageFor(s,"The recording was not saved. Your local take is still available.")}}}async revertCustomAudio(){const t=this.studyCard;if(t){this.audioMessage="";try{if(!(await m.revertAudio(t.note_id)).reverted)throw new Error("The server did not confirm the change.");this.hasCustomAudio=!1,this.revertConfirmation=!1,this.audioMessage="Automatic pronunciation restored.",await this.refreshStudyFace(t.card_id)}catch(e){this.audioMessage=this.messageFor(e,"Automatic pronunciation could not be restored.")}}}selectedDeck(){return this.decks.find(t=>t.id===this.selectedDeckId)}manualDeck(){return this.decks.find(t=>t.id===this.manualDeckId)}resetManualSelection(){this.selectedCandidate=null,this.selectedSenseRef=null,this.selectedMeaningLanguages=["de","en"],this.userMeaningDe="",this.userMeaningEn=""}selectCandidate(t){var e,s;this.selectedCandidate=t,this.selectedSenseRef=t.status==="resolved"?((s=(e=t.senses)==null?void 0:e[0])==null?void 0:s.sense_semantic_ref)??null:null}toggleMeaningLanguage(t,e){this.selectedMeaningLanguages=e?[...new Set([...this.selectedMeaningLanguages,t])]:this.selectedMeaningLanguages.filter(s=>s!==t)}async lookup(t){t.preventDefault();const e=this.lookupQuery.trim();if(!e){this.errorMessage="Enter a German word before looking it up.",this.successMessage="";return}this.lookupStatus="loading",this.lookupCandidates=[],this.lookupAssetToken="",this.resetManualSelection(),this.errorMessage="",this.successMessage="";try{const s=await m.lookup(e),i=s.candidates.map(r=>{var n,p;return{...r,status:r.status??((n=r.senses)!=null&&n.length?"resolved":"needs_gloss"),senses:(p=r.senses)==null?void 0:p.map(c=>{var g,y;return{...c,gloss:c.gloss??((y=(g=c.meanings)==null?void 0:g[0])==null?void 0:y.text)??""}})}});this.lookupCandidates=i,this.lookupAssetToken=s.asset_token,this.lookupStatus="ready";const a=i.length===1?i[0]:void 0;a&&this.selectCandidate(a)}catch(s){this.lookupStatus="error",this.errorMessage=this.messageFor(s,"German vocabulary could not be looked up.")}}userMeanings(){const t={};return this.userMeaningDe.trim()&&(t.de=this.userMeaningDe.trim()),this.userMeaningEn.trim()&&(t.en=this.userMeaningEn.trim()),Object.keys(t).length?t:void 0}async saveManualNote(t){var i;t.preventDefault();const e=this.selectedCandidate,s=this.manualDeck();if(!e||!this.lookupAssetToken){this.errorMessage="Look up and select a German vocabulary candidate before saving.",this.successMessage="";return}if(!s){this.errorMessage="Select a deck before saving this vocabulary.",this.successMessage="";return}if(!this.selectedMeaningLanguages.length){this.errorMessage="Select German, English, or both meaning languages.",this.successMessage="";return}if(e.status==="resolved"&&!this.selectedSenseRef){this.errorMessage="Select a meaning for this resolved dictionary entry.",this.successMessage="";return}if(e.status==="derived_compound"&&!((i=e.component_refs)!=null&&i.length)){this.errorMessage="This derived compound has no supported component bindings to save.",this.successMessage="";return}this.isSavingNote=!0,this.errorMessage="",this.successMessage="";try{const a=await m.createNote({asset_token:this.lookupAssetToken,lemma_semantic_ref:e.lemma_semantic_ref,sense_semantic_ref:this.selectedSenseRef,status:e.status,component_refs:e.component_refs,meaning_languages:this.selectedMeaningLanguages,deck_name:s.name,user_meanings:this.userMeanings()}),r=await this.loadDecks();if(r===null){this.errorMessage=`“${e.lemma}” may have been saved, but the deck list could not be refreshed.`;return}const n=r.find(p=>p.id===a.deck_id);if(a.deck_id!==s.id||!n){this.errorMessage=`The server did not confirm “${e.lemma}” in the selected deck. It was not reported as saved.`;return}this.selectedDeckId=n.id,this.manualDeckId=n.id,this.successMessage=`Saved “${e.lemma}” to “${n.name}”.`,this.lookupQuery="",this.lookupCandidates=[],this.lookupAssetToken="",this.lookupStatus="idle",this.resetManualSelection()}catch(a){this.successMessage="",this.errorMessage=this.messageFor(a,"Vocabulary could not be saved.")}finally{this.isSavingNote=!1}}captureKey(t){return`${t.lemma_semantic_ref}:${t.status}`}updateCaptureSpan(t){const e=t.target;this.captureSpanStart=e.selectionStart??0,this.captureSpanEnd=e.selectionEnd??0}resetCapturePicker(){this.captureCandidates=[],this.captureAssetToken="",this.captureContext=null,this.captureSelections={},this.captureDictionaryChanged=!1}async highlightCapture(t){t==null||t.preventDefault();const e=this.captureSentence,s=this.captureLessonLabel.trim(),i={start:this.captureSpanStart,end:this.captureSpanEnd};if(!e.trim()){this.captureStatus="error",this.captureError="Enter the sentence you want this card to remember.";return}if(i.start===i.end){this.captureStatus="error",this.captureError="Select the German word or phrase in the sentence before finding candidates.";return}if(!s){this.captureStatus="error",this.captureError="Add a lesson label so this capture keeps its provenance.";return}this.captureStatus="loading",this.captureError="",this.resetCapturePicker();try{const a=await m.highlight({sentence_text:e,selected_span:i,lesson_label:s});this.captureCandidates=a.candidates,this.captureAssetToken=a.asset_token,this.captureContext=a.capture_context,this.captureStatus="ready";const r=a.candidates.length===1?a.candidates[0]:void 0;r&&this.toggleCaptureCandidate(r,!0)}catch(a){this.captureStatus="error",this.captureError=this.messageFor(a,"Candidates could not be found.")}}toggleCaptureCandidate(t,e){var a,r;const s=this.captureKey(t),i={...this.captureSelections};e?i[s]={candidate:t,senseRef:t.status==="resolved"?((r=(a=t.senses)==null?void 0:a[0])==null?void 0:r.sense_semantic_ref)??null:null}:delete i[s],this.captureSelections=i}setCaptureSense(t,e){const s=this.captureKey(t),i=this.captureSelections[s];i&&(this.captureSelections={...this.captureSelections,[s]:{...i,senseRef:e}})}toggleCaptureMeaningLanguage(t){const e=this.captureMeaningLanguages;if(e.includes(t)){if(e.length===1)return;this.captureMeaningLanguages=e.filter(s=>s!==t);return}this.captureMeaningLanguages=[...e,t]}captureUserMeanings(){const t={};return this.captureUserMeaningDe.trim()&&(t.de=this.captureUserMeaningDe.trim()),this.captureUserMeaningEn.trim()&&(t.en=this.captureUserMeaningEn.trim()),Object.keys(t).length?t:void 0}async saveCapture(t){t.preventDefault();const e=this.decks.find(a=>a.id===this.captureDeckId),s=Object.values(this.captureSelections);if(!s.length)return;if(!e){this.captureError="Choose a destination deck before creating cards.";return}if(!this.captureContext||!this.captureAssetToken){this.captureError="Find candidates again before creating cards.";return}if(s.some(({candidate:a,senseRef:r})=>a.status==="resolved"&&!r)){this.captureError="Choose a dictionary meaning for every selected candidate.";return}this.isCapturing=!0,this.captureError="",this.captureDictionaryChanged=!1,this.successMessage="";try{const a=await m.captureCards({asset_token:this.captureAssetToken,deck:{name:e.name,lesson_label:this.captureContext.lesson_label},capture_context:this.captureContext,selections:s.map(({candidate:g,senseRef:y})=>({lemma_semantic_ref:g.lemma_semantic_ref,sense_semantic_ref:y,status:g.status,component_refs:g.component_refs,overrides:{meaning_langs:this.captureMeaningLanguages,user_meanings:this.captureUserMeanings()}}))}),r=await this.loadDecks(),n=r==null?void 0:r.find(g=>g.id===a.deck_id);if(!n||n.id!==e.id){this.captureError="The server did not confirm the selected destination deck. Cards were not reported as created.";return}const p=a.notes.filter(g=>g.created).length,c=a.notes.length-p;this.selectedDeckId=n.id,this.manualDeckId=n.id,this.captureDeckId=n.id,this.successMessage=`Server confirmed ${p} ${p===1?"card":"cards"} created and ${c} ${c===1?"card":"cards"} reused in “${n.name}”.`,this.captureStatus="idle",this.captureSentence="",this.captureLessonLabel="",this.captureSpanStart=0,this.captureSpanEnd=0,this.captureUserMeaningDe="",this.captureUserMeaningEn="",this.resetCapturePicker()}catch(a){a instanceof L&&a.isConflict?(this.captureDictionaryChanged=!0,this.captureError=""):this.captureError=this.messageFor(a,"Cards could not be created.")}finally{this.isCapturing=!1}}async readImportFile(t){var s;const e=(s=t.target.files)==null?void 0:s[0];if(e){this.isReadingImportFile=!0,this.errorMessage="",this.successMessage="";try{this.importText=await e.text(),this.importFileName=e.name}catch(i){this.importFileName="",this.errorMessage=this.messageFor(i,"The selected file could not be read.")}finally{this.isReadingImportFile=!1}}}async importCsv(t){t.preventDefault();const e=this.importDeckName.trim(),s=this.importText.trim();if(!e){this.errorMessage="Enter the deck name for this CSV import.",this.successMessage="";return}if(!s){this.errorMessage="Paste vocabulary lines or choose a CSV/text file before importing.",this.successMessage="";return}this.isImporting=!0,this.errorMessage="",this.successMessage="";try{const i=await m.importCsv({csv_text:s,deck_name:e}),a=await this.loadDecks();if(a===null){this.errorMessage="The import may have completed, but the deck list could not be refreshed.";return}const r=a.find(n=>n.id===i.deck_id);if(!r){this.errorMessage="The server did not return the import deck after completion. The import was not reported as successful.";return}this.selectedDeckId=r.id,this.manualDeckId=r.id,this.importDeckName=r.name,this.successMessage=`Imported ${i.total_words} ${i.total_words===1?"word":"words"} into “${r.name}”: ${i.notes_created} created, ${i.notes_reused} reused.`,this.importText="",this.importFileName=""}catch(i){this.successMessage="",this.errorMessage=this.messageFor(i,"CSV import could not be completed.")}finally{this.isImporting=!1}}async exportTsv(t){this.exportingFormat="tsv",this.errorMessage="",this.successMessage="";try{const e=await m.exportAnki(t.id),s=URL.createObjectURL(new Blob([e],{type:"text/tab-separated-values;charset=utf-8"})),i=document.createElement("a");i.href=s,i.download=`${t.name.replace(/[^a-z0-9._-]+/gi,"-")||"flashcards"}.tsv`,i.click(),URL.revokeObjectURL(s),this.successMessage=`Prepared a TSV export for “${t.name}”.`}catch(e){this.errorMessage=this.messageFor(e,"TSV export could not be prepared.")}finally{this.exportingFormat=null}}async exportApkg(t){this.exportingFormat="apkg",this.errorMessage="",this.successMessage="";try{const e=await m.exportApkg(t.id),s=URL.createObjectURL(e),i=document.createElement("a");i.href=s,i.download=`${t.name.replace(/[^a-z0-9._-]+/gi,"-")||"flashcards"}.apkg`,i.click(),URL.revokeObjectURL(s),this.successMessage=`Prepared an APKG export for “${t.name}”.`}catch(e){this.errorMessage=this.messageFor(e,"APKG export could not be prepared.")}finally{this.exportingFormat=null}}renderNotices(){return o`
      ${this.errorMessage?o`<div class="notice error" role="alert">${this.errorMessage}</div>`:u}
      ${this.successMessage?o`<div class="notice success" role="status">${this.successMessage}</div>`:u}
    `}renderDeckList(){return this.deckStatus==="loading"?o`<p class="loading" role="status">Loading decks…</p>`:this.deckStatus==="error"?o`<div class="empty"><p>We could not reach your deck list.</p><button @click=${this.loadDecks}>Try again</button></div>`:this.decks.length===0?o`<div class="empty"><p>No decks yet. Create one to begin organizing German vocabulary.</p></div>`:o`
      <ul class="deck-list" aria-label="Your decks">
        ${this.decks.map(t=>o`
          <li class="deck">
            <button class="deck-open" @click=${()=>this.openDeck(t)} aria-label=${`Open ${t.name}`}>
              <span class="deck-name">${t.name}</span>
              <span class="deck-stats">${t.card_count} ${t.card_count===1?"card":"cards"} · ${t.due_count} due · ${t.mastery_percent}% mastered</span>
            </button>
            ${this.pendingDeleteDeckId===t.id?o`
              <div class="actions confirm" aria-label=${`Confirm deletion of ${t.name}`}>
                <button class="danger" ?disabled=${this.isDeleting} @click=${()=>void this.deleteDeck(t)}>${this.isDeleting?"Deleting…":"Confirm delete"}</button>
                <button ?disabled=${this.isDeleting} @click=${()=>{this.pendingDeleteDeckId=null}}>Cancel</button>
              </div>
            `:o`
              <button class="danger" @click=${()=>{this.pendingDeleteDeckId=t.id,this.successMessage=""}}>Delete</button>
            `}
          </li>
        `)}
      </ul>
    `}renderSenseChoices(t){return o`
      <fieldset class="selection">
        <legend>Dictionary meaning</legend>
        <ul class="choice-list">
          ${t.map(e=>o`
            <li>
              <label class="choice">
                <input
                  type="radio"
                  name="sense"
                  .value=${e.sense_semantic_ref}
                  .checked=${this.selectedSenseRef===e.sense_semantic_ref}
                  @change=${()=>{this.selectedSenseRef=e.sense_semantic_ref}}
                />
                <span>${e.gloss||`Meaning ${e.ord}`}</span>
              </label>
            </li>
          `)}
        </ul>
      </fieldset>
    `}renderManualCreation(){var s;const t=this.selectedCandidate,e=this.manualDeck();return o`
      <section class="workflow" aria-labelledby="manual-title">
        <h3 id="manual-title">Add German vocabulary</h3>
        <p class="muted">Look up a German word, choose its dictionary meaning, then let the server create the note.</p>
        <form @submit=${this.lookup}>
          <label>German word
            <input
              .value=${this.lookupQuery}
              @input=${i=>{this.lookupQuery=i.target.value}}
              ?disabled=${this.lookupStatus==="loading"||this.isSavingNote}
              autocomplete="off"
              placeholder="e.g. anrufen"
            />
          </label>
          <div class="actions"><button class="primary" type="submit" ?disabled=${this.lookupStatus==="loading"||this.isSavingNote}>${this.lookupStatus==="loading"?"Looking up…":"Look up"}</button></div>
        </form>
        ${this.lookupStatus==="loading"?o`<p class="result" role="status">Looking up the active dictionary…</p>`:u}
        ${this.lookupStatus==="ready"&&!this.lookupCandidates.length?o`<p class="result">No dictionary candidate was returned. Try a different German form.</p>`:u}
        ${this.lookupCandidates.length?o`
          <fieldset class="selection">
            <legend>Select vocabulary</legend>
            <ul class="candidate-list">
              ${this.lookupCandidates.map(i=>o`
                <li>
                  <button
                    class="candidate ${t===i?"selected":""}"
                    type="button"
                    @click=${()=>this.selectCandidate(i)}
                    aria-pressed=${t===i?"true":"false"}
                  >
                    ${i.lemma} · ${i.pos}
                    <small>${i.status==="resolved"?"Dictionary entry":i.status.replace("_"," ")}</small>
                  </button>
                </li>
              `)}
            </ul>
          </fieldset>
        `:u}
        ${t?o`
          <form @submit=${this.saveManualNote}>
            ${t.status==="resolved"?(s=t.senses)!=null&&s.length?this.renderSenseChoices(t.senses):o`<p class="result">This result has no selectable sense and cannot be saved as a resolved note.</p>`:u}
            ${t.status==="derived_compound"?o`<p class="result">The server will retain this compound’s supported component bindings.</p>`:u}
            <label>Deck
              <select
                .value=${e?String(e.id):""}
                @change=${i=>{const a=i.target.value;this.manualDeckId=a?Number(a):null}}
                ?disabled=${this.isSavingNote}
              >
                <option value="">Select a deck</option>
                ${this.decks.map(i=>o`<option value=${i.id}>${i.name}</option>`)}
              </select>
            </label>
            <fieldset class="selection">
              <legend>Meaning languages</legend>
              <label class="choice"><input type="checkbox" .checked=${this.selectedMeaningLanguages.includes("de")} @change=${i=>this.toggleMeaningLanguage("de",i.target.checked)} /> German (DE)</label>
              <label class="choice"><input type="checkbox" .checked=${this.selectedMeaningLanguages.includes("en")} @change=${i=>this.toggleMeaningLanguage("en",i.target.checked)} /> English (EN)</label>
            </fieldset>
            <label>Your German meaning <span class="muted">(optional)</span>
              <input .value=${this.userMeaningDe} @input=${i=>{this.userMeaningDe=i.target.value}} ?disabled=${this.isSavingNote} autocomplete="off" />
            </label>
            <label>Your English meaning <span class="muted">(optional)</span>
              <input .value=${this.userMeaningEn} @input=${i=>{this.userMeaningEn=i.target.value}} ?disabled=${this.isSavingNote} autocomplete="off" />
            </label>
            <div class="actions"><button class="primary" type="submit" ?disabled=${this.isSavingNote}>${this.isSavingNote?"Saving…":"Save vocabulary"}</button></div>
          </form>
        `:u}
      </section>
    `}renderCaptureCreation(t){const e=Object.keys(this.captureSelections).length,s=this.decks.find(a=>a.id===this.captureDeckId),i=this.captureSentence.slice(this.captureSpanStart,this.captureSpanEnd);return o`
      <section class="workflow capture-workflow" aria-labelledby="capture-title">
        <h3 id="capture-title">Capture from a sentence</h3>
        <p class="muted">Paste or type a sentence, select its German word or phrase, then choose the cards to create.</p>
        <form @submit=${this.highlightCapture}>
          <label>Sentence text
            <textarea
              .value=${this.captureSentence}
              @input=${a=>{this.captureSentence=a.target.value,this.updateCaptureSpan(a),this.resetCapturePicker(),this.captureStatus="idle",this.captureError=""}}
              @select=${this.updateCaptureSpan}
              @keyup=${this.updateCaptureSpan}
              @click=${this.updateCaptureSpan}
              ?disabled=${this.captureStatus==="loading"||this.isCapturing}
              placeholder="Ich rufe dich morgen an."
            ></textarea>
          </label>
          <p class="selection-preview" aria-live="polite">${i?o`Selected: <strong>“${i}”</strong>`:"Select a German word or phrase in the sentence."}</p>
          <label>Lesson label
            <input
              .value=${this.captureLessonLabel}
              @input=${a=>{this.captureLessonLabel=a.target.value,this.resetCapturePicker(),this.captureStatus="idle",this.captureError=""}}
              ?disabled=${this.captureStatus==="loading"||this.isCapturing}
              autocomplete="off"
              placeholder="Lesson 4 · Telephone calls"
            />
          </label>
          <div class="actions">
            <button class="primary" type="submit" ?disabled=${this.captureStatus==="loading"||this.isCapturing}>${this.captureStatus==="loading"?"Finding candidates…":"Find candidates"}</button>
          </div>
        </form>
        ${this.captureStatus==="loading"?o`<p class="result" role="status">Checking the active dictionary…</p>`:u}
        ${this.captureStatus==="error"?o`<div class="capture-state error" role="alert"><p>${this.captureError}</p><button @click=${()=>void this.highlightCapture()}>Try again</button></div>`:u}
        ${this.captureStatus==="ready"&&this.captureCandidates.length===0?o`<div class="capture-state"><p>No dictionary candidates were found for “${i}”. Adjust the selected text and try again.</p></div>`:u}
        ${this.captureCandidates.length?o`
          <form class="capture-picker" @submit=${this.saveCapture}>
            <fieldset class="selection">
              <legend>Choose vocabulary <span class="muted">(select one or more)</span></legend>
              <p class="result">Each checked German candidate becomes its own card. You can select multiple candidates.</p>
              <ul class="candidate-list">
                ${this.captureCandidates.map(a=>{var p;const r=this.captureKey(a),n=this.captureSelections[r];return o`
                    <li class="capture-candidate ${n?"chosen":""}">
                      <label class="candidate-choice">
                        <input
                          type="checkbox"
                          .checked=${!!n}
                          @change=${c=>this.toggleCaptureCandidate(a,c.target.checked)}
                          ?disabled=${this.isCapturing}
                        />
                        <span><strong class="lemma">${a.lemma}</strong> <span class="caption">${a.pos}</span></span>
                      </label>
                      ${n&&a.status==="resolved"?(p=a.senses)!=null&&p.length?o`
                        <fieldset class="sense-choices">
                          <legend>Dictionary meaning for ${a.lemma}</legend>
                          ${a.senses.map(c=>o`
                            <label class="choice">
                              <input type="radio" name=${`capture-sense-${r}`} .value=${c.sense_semantic_ref} .checked=${n.senseRef===c.sense_semantic_ref} @change=${()=>this.setCaptureSense(a,c.sense_semantic_ref)} ?disabled=${this.isCapturing} />
                              ${c.gloss||`Meaning ${c.ord}`}
                            </label>
                          `)}
                        </fieldset>
                      `:o`<p class="result">This entry has no selectable dictionary meaning.</p>`:u}
                      ${n&&a.status==="derived_compound"?o`<p class="result">The server will preserve the compound’s dictionary component bindings.</p>`:u}
                    </li>
                  `})}
              </ul>
            </fieldset>
            ${this.captureDictionaryChanged?o`
              <div class="capture-state warning" role="alert">
                <p>The dictionary changed while you were choosing cards. Your selections have not been saved.</p>
                <button type="button" @click=${()=>void this.highlightCapture()}>Find fresh candidates</button>
              </div>
            `:u}
            ${this.captureError?o`<div class="capture-state error" role="alert"><p>${this.captureError}</p></div>`:u}
            <fieldset class="selection language-chips">
              <legend>Meaning languages</legend>
              <p class="result">Choose German, English, or both. At least one language stays selected.</p>
              ${["de","en"].map(a=>o`
                <button
                  class="chip ${this.captureMeaningLanguages.includes(a)?"selected":""}"
                  type="button"
                  aria-pressed=${this.captureMeaningLanguages.includes(a)?"true":"false"}
                  @click=${()=>this.toggleCaptureMeaningLanguage(a)}
                  ?disabled=${this.isCapturing||this.captureMeaningLanguages.length===1&&this.captureMeaningLanguages.includes(a)}
                >${a==="de"?"German · DE":"English · EN"}</button>
              `)}
            </fieldset>
            ${this.captureMeaningLanguages.includes("de")?o`<label>Your German meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningDe} @input=${a=>{this.captureUserMeaningDe=a.target.value}} ?disabled=${this.isCapturing} autocomplete="off" /></label>`:u}
            ${this.captureMeaningLanguages.includes("en")?o`<label>Your English meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningEn} @input=${a=>{this.captureUserMeaningEn=a.target.value}} ?disabled=${this.isCapturing} autocomplete="off" /></label>`:u}
            <label>Destination deck
              <select .value=${String(s?s.id:t.id)} @change=${a=>{const r=a.target.value;this.captureDeckId=r?Number(r):null}} ?disabled=${this.isCapturing}>
                <option value="">Select a deck</option>
                ${this.decks.map(a=>o`<option value=${a.id}>${a.name}</option>`)}
              </select>
            </label>
            <div class="actions create-actions">
              <button class="primary" type="submit" ?disabled=${e===0||this.isCapturing||this.captureDictionaryChanged}>${this.isCapturing?"Creating cards…":`Create ${e||""} card${e===1?"":"s"}`}</button>
              ${e===0?o`<p class="disabled-explanation">Select at least one candidate to create cards.</p>`:u}
            </div>
          </form>
        `:u}
      </section>
    `}renderImportExport(t){return o`
      <section class="workflow" aria-labelledby="import-export-title">
        <h3 id="import-export-title">Import & export</h3>
        <form @submit=${this.importCsv}>
          <label>CSV import deck name
            <input
              .value=${this.importDeckName}
              @input=${e=>{this.importDeckName=e.target.value}}
              list="deck-names"
              ?disabled=${this.isImporting||this.isReadingImportFile}
              autocomplete="off"
            />
          </label>
          <datalist id="deck-names">${this.decks.map(e=>o`<option value=${e.name}></option>`)}</datalist>
          <label>Vocabulary lines
            <textarea .value=${this.importText} @input=${e=>{this.importText=e.target.value}} ?disabled=${this.isImporting||this.isReadingImportFile} placeholder="Haus&#10;anrufen&#10;Feierabend"></textarea>
          </label>
          <label>Or choose a CSV/text file
            <input type="file" accept=".csv,.txt,text/csv,text/plain" @change=${this.readImportFile} ?disabled=${this.isImporting||this.isReadingImportFile} />
          </label>
          ${this.isReadingImportFile?o`<p class="result" role="status">Reading file…</p>`:u}
          ${this.importFileName?o`<p class="result">Using text from ${this.importFileName}.</p>`:u}
          <div class="actions"><button class="primary" type="submit" ?disabled=${this.isImporting||this.isReadingImportFile}>${this.isImporting?"Importing…":"Import CSV"}</button></div>
        </form>
        <div class="workflow-grid">
          <div>
            <h3>APKG export</h3>
            <p class="muted">Download the selected deck as a ready-to-import Anki package.</p>
            <button class="primary" @click=${()=>void this.exportApkg(t)} ?disabled=${this.exportingFormat!==null}>${this.exportingFormat==="apkg"?"Preparing APKG…":`Export “${t.name}” APKG`}</button>
          </div>
          <div>
            <h3>TSV export</h3>
            <p class="muted">Secondary export for the available Anki TSV format.</p>
            <button @click=${()=>void this.exportTsv(t)} ?disabled=${this.exportingFormat!==null}>${this.exportingFormat==="tsv"?"Preparing TSV…":`Export “${t.name}” TSV`}</button>
          </div>
          <div>
            <h3>TSV import</h3>
            <p class="muted">Pending — this product has no accepted TSV import contract yet.</p>
            <button class="pending" disabled>TSV import pending</button>
          </div>
          <div>
            <h3>APKG import</h3>
            <p class="muted">Pending — this product has no accepted APKG import contract yet.</p>
            <button class="pending" disabled>APKG import pending</button>
          </div>
        </div>
      </section>
    `}renderSimplePronunciation(){return o`
      <div class="pronunciation-simple">
        <div class="audio-actions">
          <button type="button" @click=${()=>void this.playPronunciation()} ?disabled=${this.audioStatus==="loading"}>
            ${this.audioStatus==="loading"?"Loading pronunciation…":this.audioStatus==="playing"?"Playing pronunciation…":"Play pronunciation"}
          </button>
          <span class="caption">Press R to replay</span>
        </div>
        ${this.audioMessage?o`<p class="inline-status ${this.audioStatus==="unavailable"?"error":""}" role=${this.audioStatus==="unavailable"?"alert":"status"}>${this.audioMessage}</p>`:u}
      </div>
    `}renderPronunciationManagement(){const t=this.recordingStatus==="save-error";return o`
      <section class="pronunciation" aria-labelledby="pronunciation-title">
        <h3 id="pronunciation-title">Custom pronunciation</h3>
        ${this.hasCustomAudio?o`
          <div class="audio-actions">
            <button type="button" @click=${()=>{this.showRecordingControls=!this.showRecordingControls,this.revertConfirmation=!1}}>
              ${this.showRecordingControls?"Keep current pronunciation":"Replace pronunciation"}
            </button>
            ${this.revertConfirmation?o`
              <span class="caption">Replace your custom pronunciation with automatic pronunciation?</span>
              <button class="danger" type="button" @click=${()=>void this.revertCustomAudio()}>Confirm revert to automatic</button>
              <button type="button" @click=${()=>{this.revertConfirmation=!1}}>Cancel</button>
            `:o`<button class="danger" type="button" @click=${()=>{this.revertConfirmation=!0,this.showRecordingControls=!1}}>Revert to automatic</button>`}
          </div>
        `:o`<button type="button" @click=${()=>{this.showRecordingControls=!this.showRecordingControls}}>Add your pronunciation</button>`}
        ${this.showRecordingControls?o`
          <div class="local-take">
            <p class="muted">Record a take or choose an audio file. It stays only in this browser until you save it.</p>
            ${this.recordingBlob?o`
              <p class="inline-status">Local recording ready to preview and save.</p>
              <audio class="audio-preview" controls src=${this.recordingPreviewUrl}></audio>
            `:u}
            ${t?o`
              <p class="inline-status error" role="alert">${this.recordingError}</p>
              <div class="recording-actions">
                <button class="primary" type="button" @click=${()=>void this.saveRecording()}>Try again</button>
                <button class="danger" type="button" @click=${this.discardRecording}>Discard recording</button>
              </div>
            `:o`
              <div class="recording-actions">
                ${this.recordingStatus==="recording"?o`<button class="danger" type="button" @click=${this.stopRecording}>Stop recording</button>`:o`<button type="button" @click=${()=>void this.startRecording()} ?disabled=${this.recordingStatus==="saving"}>Record pronunciation</button>`}
                <label>Choose audio file
                  <input type="file" accept="audio/*" @change=${this.selectAudioFile} ?disabled=${this.recordingStatus==="recording"||this.recordingStatus==="saving"} />
                </label>
                ${this.recordingBlob?o`
                  <button class="primary" type="button" @click=${()=>void this.saveRecording()} ?disabled=${this.recordingStatus==="saving"}>${this.recordingStatus==="saving"?"Saving pronunciation…":"Save recording"}</button>
                  <button class="danger" type="button" @click=${this.discardRecording} ?disabled=${this.recordingStatus==="saving"}>Discard recording</button>
                `:u}
              </div>
              ${this.recordingError?o`<p class="inline-status error" role="alert">${this.recordingError}</p>`:u}
            `}
          </div>
        `:u}
      </section>
    `}renderMeaningEditor(t){return o`
      <section class="edit-meanings" aria-labelledby="meaning-edit-title">
        <h3 id="meaning-edit-title">Your meanings</h3>
        <p class="muted">Save your wording for either language, or remove an existing personal meaning to return to the card’s available meaning.</p>
        ${["de","en"].map(e=>{const s=this.meaningFor(t,e),i=!!(s!=null&&s.is_user_authored);return o`
            <div class="gloss-row">
              <label>Your ${e==="de"?"German":"English"} meaning
                <input
                  .value=${this.glossDrafts[e]}
                  @input=${r=>{this.glossDrafts={...this.glossDrafts,[e]:r.target.value}}}
                  ?disabled=${this.glossSavingLanguage===e}
                  autocomplete="off"
                />
              </label>
              <button type="button" @click=${()=>void this.saveGloss(e)} ?disabled=${this.glossSavingLanguage===e||!this.glossDrafts[e].trim()}>
                ${this.glossSavingLanguage===e?"Saving…":"Save"}
              </button>
              ${i?o`<button class="danger" type="button" @click=${()=>void this.deleteGloss(e)} ?disabled=${this.glossSavingLanguage===e}>Remove</button>`:u}
            </div>
          `})}
        ${this.glossState?o`<p class="inline-status" role="status">${this.glossState}</p>`:u}
        ${this.glossError?o`<p class="inline-status error" role="alert">${this.glossError}</p>`:u}
      </section>
    `}renderStudyCard(t){const e=this.meaningFor(t,"de"),s=this.meaningFor(t,"en"),i=t.back.examples[0],a=t.back.examples.slice(1),r=t.back.meanings.flatMap(n=>n.lines.slice(1).map(p=>`${n.heading}: ${p}`));return o`
      <div class="card-stage">
        <div class="card-side">
          <span class="front-label">German vocabulary</span>
          <h2 class="study-lemma">${t.front.display_headword}</h2>
          <p class="study-meta">${t.front.pos}${t.front.ipa?` · ${t.front.ipa}`:""}</p>
          ${this.isRevealed?o`
            <div class="card-side" data-study-answer tabindex="-1">
              <hr class="answer-rule" />
              <span class="front-label">Answer</span>
              <p class="meaning"><span class="meaning-label">German</span><br />${(e==null?void 0:e.lines[0])??"No German learner meaning is available."}</p>
              ${s?o`<p class="meaning"><span class="meaning-label">English</span><br />${s.lines[0]??""}</p>`:u}
              ${i?o`<p class="example">${i.de}${i.en?o`<span class="example-translation">${i.en}</span>`:u}</p>`:u}
              ${this.renderSimplePronunciation()}
              <div class="extra-info-row">
                <button
                  type="button"
                  aria-expanded=${this.extraInfoOpen?"true":"false"}
                  aria-controls="extra-info-panel"
                  @click=${this.toggleExtraInfo}
                >${this.extraInfoOpen?"Hide extra info":"Show extra info"}</button>
                <label class="always-extra-toggle">
                  <input
                    type="checkbox"
                    .checked=${this.alwaysShowExtraInfo}
                    @change=${n=>this.setAlwaysShowExtraInfo(n.target.checked)}
                  />
                  Always show extra info
                </label>
              </div>
              ${this.extraInfoOpen?o`
                <div class="extra-info" id="extra-info-panel">
                  <div class="detail-block"><span class="meaning-label">Grammar</span><p>${t.back.grammar.lines.join(" · ")||t.back.pos}</p></div>
                  ${r.length?o`<div class="detail-block"><span class="meaning-label">Extended notes</span><ul>${r.map(n=>o`<li>${n}</li>`)}</ul></div>`:u}
                  ${a.length?o`<div class="detail-block"><span class="meaning-label">Additional examples</span>${a.map(n=>o`<p class="example">${n.de}${n.en?o`<span class="example-translation">${n.en}</span>`:u}</p>`)}</div>`:u}
                  ${this.renderPronunciationManagement()}
                  ${this.renderMeaningEditor(t)}
                </div>
              `:u}
              <div>
                <p class="front-label">How well did you know it?</p>
                <div class="confidence-grid">
                  ${Ye.map(([n,p])=>o`
                    <button class="confidence" type="button" ?disabled=${this.isReviewing||!!this.recordingBlob} @click=${()=>void this.submitConfidence(Number(n))}>
                      <span class="confidence-number">${n}</span><span class="confidence-text">${p}</span>
                    </button>
                  `)}
                </div>
              </div>
              ${this.isReviewing?o`<p class="inline-status" role="status">Saving your confidence…</p>`:u}
              ${this.recordingBlob?o`<p class="inline-status">Save or discard the local recording before choosing a confidence.</p>`:u}
            </div>
          `:o`
            <button class="primary reveal-action" type="button" @click=${this.revealCard}>Reveal answer <span class="caption">Space</span></button>
          `}
        </div>
      </div>
    `}renderStudy(){const t=this.decks.find(e=>e.id===this.studyDeckId);return o`
      <main class="study" aria-labelledby="study-title">
        <div class="study-heading">
          <div><p class="caption">Study</p><h2 id="study-title">${t?t.name:"All due cards"}</h2></div>
          <button type="button" @click=${()=>void this.loadStudyCard()} ?disabled=${this.studyStatus==="loading"}>${this.studyStatus==="loading"?"Loading…":"Refresh"}</button>
        </div>
        ${this.studyStatus==="ready"&&this.studyError?o`<p class="inline-status error" role="alert">${this.studyError}</p>`:u}
        ${this.studyStatus==="loading"?o`<div class="card-stage study-state" role="status">Loading the next due card…</div>`:u}
        ${this.studyStatus==="error"?o`<div class="card-stage study-state"><div><h2>Could not load a card</h2><p class="inline-status error" role="alert">${this.studyError}</p><button class="primary" type="button" @click=${()=>void this.loadStudyCard()}>Try again</button></div></div>`:u}
        ${this.studyStatus==="empty"?o`<div class="card-stage study-state" data-study-empty tabindex="-1"><div><h2>Nothing due right now</h2><p class="muted">Your next due card will appear here when the server has one ready.</p><button type="button" @click=${()=>void this.loadStudyCard()}>Check again</button></div></div>`:u}
        ${this.studyStatus==="ready"&&this.studyCard?this.renderStudyCard(this.studyCard):u}
      </main>
    `}async loadDictionarySettings(){this.dictionarySettingsStatus="loading",this.dictionaryActionError="";try{const t=await m.getDictionarySettings();this.dictionarySettings=t,this.dictionaryMode=t.mode,this.dictionarySettingsStatus="ready",t.mode==="unconfigured"&&this.view!=="study"&&this.view!=="chooser"&&(this.view="chooser"),t.mode!=="unconfigured"&&this.view==="chooser"&&(this.view="decks")}catch(t){this.dictionarySettingsStatus="error",this.dictionaryActionError=this.messageFor(t,"Could not read the dictionary settings.")}}async useOnline(){this.dictionaryAction="switching-online",this.dictionaryActionMessage="",this.dictionaryActionError="";try{await m.useOnline(),this.dictionaryActionMessage="Now using Online for this session. The canonical Offline dictionary will not be removed.",await this.loadDictionarySettings()}catch(t){this.dictionaryActionError=this.messageFor(t,"Could not switch to Online for this session.")}finally{this.dictionaryAction="idle"}}async useOffline(){this.dictionaryAction="switching-offline",this.dictionaryActionMessage="",this.dictionaryActionError="";try{await m.useOffline(),this.dictionaryActionMessage="Now using Offline for this session.",await this.loadDictionarySettings()}catch(t){this.dictionaryActionError=this.messageFor(t,"Could not switch to Offline for this session.")}finally{this.dictionaryAction="idle"}}async installOffline(){this.dictionaryAction="installing",this.dictionaryActionMessage="",this.dictionaryActionError="";try{const t=await m.installOffline();t.status==="started"?(this.dictionaryActionMessage="Download started. Progress is shown below; the Settings view refreshes automatically.",await this.pollInstallProgress()):this.dictionaryActionMessage=`Installed full Offline dictionary (status: ${t.status}).`,await this.loadDictionarySettings()}catch(t){this.dictionaryActionError=this.messageFor(t,"Could not install the full Offline dictionary.")}finally{this.dictionaryAction="idle"}}async pollInstallProgress(){for(let t=0;t<120;t++){await new Promise(e=>setTimeout(e,1e3));try{const e=await m.getDictionarySettings();this.dictionarySettings=e,this.dictionaryMode=e.mode;const s=e.install_progress;if(!s||s.status==="idle")return;if(s.status==="installed"){this.dictionaryActionMessage="Installed full Offline dictionary.";return}if(s.status==="failed"){this.dictionaryActionError=s.error||"Offline download failed.";return}const i=s.percent.toFixed(1),a=s.downloaded_bytes.toLocaleString(),r=s.total_bytes?s.total_bytes.toLocaleString():"unknown";this.dictionaryActionMessage=`Downloading… ${a} / ${r} bytes (${i}%).`}catch{return}}}async removeOffline(){this.dictionaryAction="removing",this.dictionaryActionMessage="",this.dictionaryActionError="";try{const t=await m.removeOffline();this.dictionaryActionMessage=`Removed Offline dictionary: ${t.detail}`,this.confirmRemoveOffline=!1,await this.loadDictionarySettings()}catch(t){this.dictionaryActionError=this.messageFor(t,"Could not remove the Offline dictionary.")}finally{this.dictionaryAction="idle"}}async clearOnlineCache(){this.dictionaryAction="clearing",this.dictionaryActionMessage="",this.dictionaryActionError="";try{await m.clearOnlineCache(),this.dictionaryActionMessage="Online cache cleared.",await this.loadDictionarySettings()}catch(t){this.dictionaryActionError=this.messageFor(t,"Could not clear the Online cache.")}finally{this.dictionaryAction="idle"}}renderChooser(){return o`
      <main class="panel" aria-labelledby="chooser-title">
        <h2 id="chooser-title">Choose how to use the dictionary</h2>
        <p class="muted">
          No canonical full Offline dictionary is available yet. Pick how this
          process should serve the vocabulary:
        </p>
        <div class="workflow-grid">
          <section class="workflow" aria-labelledby="chooser-online-title">
            <h3 id="chooser-online-title">Use Online</h3>
            <p>Start now without downloading the full dictionary. Online applies
              to the current session only.</p>
            <button class="primary" type="button" @click=${()=>void this.useOnline()} ?disabled=${this.dictionaryAction!=="idle"}>
              ${this.dictionaryAction==="switching-online"?"Switching…":"Use Online"}
            </button>
          </section>
          <section class="workflow" aria-labelledby="chooser-offline-title">
            <h3 id="chooser-offline-title">Download for Offline use</h3>
            <p>Download ~945 MB and work without internet afterward. The
              free-space preflight happens before any download begins.</p>
            <button type="button" @click=${()=>void this.installOffline()} ?disabled=${this.dictionaryAction!=="idle"}>
              ${this.dictionaryAction==="installing"?"Starting install…":"Download for Offline use"}
            </button>
          </section>
        </div>
        ${this.dictionaryActionError?o`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>`:u}
      </main>
    `}renderSettings(){const t=this.dictionarySettings,e=this.dictionaryMode==="unconfigured"&&(t==null?void 0:t.canonical_offline_valid)!==!0;return o`
      <main class="panel" aria-labelledby="settings-title">
        <div class="toolbar"><h2 id="settings-title">Dictionary</h2><button @click=${()=>void this.loadDictionarySettings()} ?disabled=${this.dictionarySettingsStatus==="loading"}>${this.dictionarySettingsStatus==="loading"?"Refreshing…":"Refresh"}</button></div>
        ${this.dictionarySettingsStatus==="error"?o`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>`:u}
        ${e?this.renderChooserInline():u}
        ${t?o`
          <dl class="settings-meta">
            <dt>Mode</dt><dd data-testid="dictionary-mode">${t.mode}</dd>
            <dt>Canonical Offline</dt><dd><code>${t.canonical_offline_path}</code></dd>
            <dt>Present</dt><dd>${t.canonical_offline_present?"yes":"no"}</dd>
            <dt>Valid</dt><dd>${t.canonical_offline_valid?"yes":"no"}</dd>
            ${t.online_info?o`
              <dt>Online dataset token</dt><dd><code>${t.online_info.dataset_token.slice(0,16)}…</code></dd>
            `:u}
            ${t.install_progress&&t.install_progress.status!=="idle"?o`
              <dt>Download progress</dt><dd data-testid="install-progress">
                ${t.install_progress.downloaded_bytes.toLocaleString()} /
                ${t.install_progress.total_bytes?t.install_progress.total_bytes.toLocaleString():"unknown"} bytes
                (${t.install_progress.percent.toFixed(1)}%) — ${t.install_progress.status}
              </dd>
            `:u}
          </dl>
        `:u}
        <div class="workflow-grid">
          <section class="workflow" aria-labelledby="online-action-title">
            <h3 id="online-action-title">Online</h3>
            <p>${(t==null?void 0:t.mode)==="online"?"Online is active for this session.":"Use the trusted Online dictionary for this session only."}</p>
            <button class="primary" type="button" @click=${()=>void this.useOnline()} ?disabled=${this.dictionaryAction!=="idle"||(t==null?void 0:t.mode)==="online"}>
              ${this.dictionaryAction==="switching-online"?"Switching…":"Use Online for this session"}
            </button>
            <button type="button" @click=${()=>void this.clearOnlineCache()} ?disabled=${this.dictionaryAction!=="idle"||!(t!=null&&t.online_active)}>
              ${this.dictionaryAction==="clearing"?"Clearing…":"Clear Online cache"}
            </button>
          </section>
          <section class="workflow" aria-labelledby="offline-action-title">
            <h3 id="offline-action-title">Offline</h3>
            <p>${(t==null?void 0:t.mode)==="offline"?"Offline is active for this session.":"Activate the trusted full Offline dictionary for this session."}</p>
            <button class="primary" type="button" @click=${()=>void this.useOffline()} ?disabled=${this.dictionaryAction!=="idle"||(t==null?void 0:t.mode)==="offline"||!(t!=null&&t.canonical_offline_valid)}>
              ${this.dictionaryAction==="switching-offline"?"Switching…":"Use Offline"}
            </button>
            <button type="button" @click=${()=>void this.installOffline()} ?disabled=${this.dictionaryAction!=="idle"||(t==null?void 0:t.canonical_offline_valid)===!0}>
              ${this.dictionaryAction==="installing"?"Starting install…":"Download for Offline use"}
            </button>
            ${(t==null?void 0:t.mode)==="offline"&&!this.confirmRemoveOffline?o`
              <button class="danger" type="button" @click=${()=>{this.confirmRemoveOffline=!0}} ?disabled=${this.dictionaryAction!=="idle"}>
                Remove Offline dictionary
              </button>
            `:u}
            ${this.confirmRemoveOffline?o`
              <div class="confirm" role="alertdialog">
                <p>Remove the canonical Offline dictionary while Online is active? Choose another mode (Online for this session) first if Offline is in use.</p>
                <button class="danger" type="button" @click=${()=>void this.removeOffline()} ?disabled=${this.dictionaryAction!=="idle"}>Confirm remove Offline</button>
                <button type="button" @click=${()=>{this.confirmRemoveOffline=!1}}>Cancel</button>
              </div>
            `:u}
          </section>
        </div>
        ${this.dictionaryActionMessage?o`<p class="inline-status" role="status">${this.dictionaryActionMessage}</p>`:u}
        ${this.dictionaryActionError?o`<p class="inline-status error" role="alert">${this.dictionaryActionError}</p>`:u}
      </main>
    `}renderChooserInline(){return o`
      <section class="panel" aria-labelledby="inline-chooser-title">
        <h3 id="inline-chooser-title">Choose how to use the dictionary</h3>
        <p class="muted">No canonical full Offline dictionary is available. Online applies to this session only.</p>
        <div class="actions">
          <button class="primary" type="button" @click=${()=>void this.useOnline()} ?disabled=${this.dictionaryAction!=="idle"}>
            ${this.dictionaryAction==="switching-online"?"Switching…":"Use Online"}
          </button>
          <button type="button" @click=${()=>void this.installOffline()} ?disabled=${this.dictionaryAction!=="idle"}>
            ${this.dictionaryAction==="installing"?"Starting install…":"Download for Offline use"}
          </button>
        </div>
      </section>
    `}renderDeckDetail(t){return o`
      <section class="panel" aria-labelledby="deck-title">
        <div class="deck-heading">
          <div>
            <h2 id="deck-title">${t.name}</h2>
            <p class="muted">${t.card_count} ${t.card_count===1?"card":"cards"} · ${t.due_count} due · ${t.mastery_percent}% mastered</p>
          </div>
          <div class="actions"><button class="primary" @click=${()=>void this.openStudy(t.id)}>Study this deck</button><button @click=${()=>{this.selectedDeckId=null,this.view="decks"}}>All decks</button></div>
        </div>
        <p>Card data and review scheduling remain on the server.</p>
        <div class="workflow-grid">
          ${this.renderCaptureCreation(t)}
          ${this.renderManualCreation()}
          ${this.renderImportExport(t)}
        </div>
      </section>
    `}render(){const t=this.selectedDeck(),e=this.deckStatus!=="ready"||!t;return o`
      <div class="shell">
        <header>
          <div>
            <h1>Wortlaut</h1>
            <div class="subtitle">German vocabulary</div>
          </div>
          <nav class="primary-nav" aria-label="Main navigation">
            <button type="button" aria-current=${this.view==="study"?"false":"page"} @click=${()=>{this.view="decks",this.selectedDeckId=null}}>Decks</button>
            <button type="button" aria-current=${this.view==="study"?"page":"false"} @click=${()=>void this.openStudy()}>Study due</button>
            <button type="button" aria-current=${this.view==="settings"||this.view==="chooser"?"page":"false"} @click=${()=>{this.view="settings",this.loadDictionarySettings()}}>Settings</button>
            <button type="button" @click=${this.loadDecks} ?disabled=${this.deckStatus==="loading"}>${this.deckStatus==="loading"?"Refreshing…":"Refresh decks"}</button>
          </nav>
        </header>
        ${this.renderNotices()}
        ${this.view==="chooser"?this.renderChooser():this.view==="settings"?this.renderSettings():this.view==="study"?this.renderStudy():e?o`
          <main class="panel">
            <div class="toolbar"><h2>Your decks</h2><span class="muted" aria-live="polite">${this.deckStatus==="ready"?"Server-synced":""}</span></div>
            <form class="form-row" @submit=${this.createDeck}>
              <label>New deck name
                <input .value=${this.newDeckName} @input=${s=>{this.newDeckName=s.target.value}} ?disabled=${this.isCreating} maxlength="200" autocomplete="off" />
              </label>
              <button class="primary" type="submit" ?disabled=${this.isCreating}>${this.isCreating?"Creating…":"Create deck"}</button>
            </form>
            ${this.renderDeckList()}
          </main>
        `:this.renderDeckDetail(t)}
      </div>
      <nav class="bottom-nav" aria-label="Main navigation">
        <button type="button" aria-current=${this.view==="study"?"false":"page"} @click=${()=>{this.view="decks",this.selectedDeckId=null}}>Decks</button>
        <button type="button" aria-current=${this.view==="study"?"page":"false"} @click=${()=>void this.openStudy()}>Study due</button>
      </nav>
    `}};l.styles=ve`
    :host { display: block; min-height: 100vh; color: var(--fg); background: var(--bg); font-family: var(--font-sans); }
    .shell { max-width: 1280px; margin: 0 auto; padding: var(--space-48) var(--space-16); }
    header { display: flex; align-items: end; justify-content: space-between; gap: var(--space-16); margin-bottom: var(--space-32); }
    h1, h2, h3, p { margin-top: 0; }
    h1, h2, h3 { font-family: var(--font-display); font-weight: 600; letter-spacing: -.02em; }
    h1 { margin-bottom: var(--space-4); font-size: clamp(2rem, 5vw, 3.25rem); }
    h2 { margin-bottom: var(--space-8); font-size: 1.75rem; }
    .subtitle, .muted, .result, .caption { color: var(--muted); }
    .caption { font-family: var(--font-mono); font-size: .75rem; letter-spacing: .04em; text-transform: uppercase; }
    .panel { padding: var(--space-32); border: 1px solid var(--border); border-radius: var(--radius-panel); background: var(--surface); box-shadow: var(--shadow-sm); }
    .toolbar, .deck-heading, .form-row, .actions { display: flex; gap: var(--space-12); align-items: center; }
    .toolbar, .deck-heading { justify-content: space-between; }
    .form-row { margin: var(--space-24) 0; align-items: end; }
    label { display: grid; gap: var(--space-4); flex: 1; font-size: .875rem; font-weight: 600; }
    input, select, textarea { width: 100%; padding: 10px var(--space-12); color: var(--fg); background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-control); font: inherit; }
    textarea { min-height: 8rem; resize: vertical; }
    button { min-height: 2.6rem; padding: var(--space-8) var(--space-16); color: var(--fg); border: 1px solid var(--border); border-radius: var(--radius-control); background: var(--surface); cursor: pointer; font: inherit; font-weight: 600; }
    button:hover:not(:disabled) { border-color: var(--accent); }
    button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent), white 65%); outline-offset: 2px; }
    button.primary { color: white; border-color: var(--accent); background: var(--accent); }
    button.primary:hover:not(:disabled) { filter: brightness(.94); }
    button.danger { color: var(--danger); }
    button:disabled { cursor: not-allowed; opacity: .55; }
    .notice, .capture-state { margin-bottom: var(--space-16); padding: var(--space-12); border: 1px solid var(--border); border-radius: var(--radius-control); }
    .notice.error, .capture-state.error { color: var(--danger); background: color-mix(in oklch, var(--danger), white 94%); }
    .notice.success { color: var(--success); background: color-mix(in oklch, var(--success), white 94%); }
    .capture-state.warning { border-color: var(--warning); background: color-mix(in oklch, var(--warning), white 91%); }
    .capture-state p { margin-bottom: var(--space-8); }
    .capture-state p:last-child { margin-bottom: 0; }
    .deck-list { display: grid; gap: var(--space-12); padding: 0; margin: var(--space-24) 0 0; list-style: none; }
    .deck { display: grid; grid-template-columns: 1fr auto; gap: var(--space-16); align-items: center; padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); }
    .deck-open { min-height: 0; padding: 0; border: 0; background: transparent; text-align: left; }
    .deck-open:hover:not(:disabled) { background: transparent; text-decoration: underline; }
    .deck-name { display: block; font-family: var(--font-display); font-size: 1.2rem; font-weight: 600; }
    .deck-stats { display: block; margin-top: var(--space-4); color: var(--muted); font-family: var(--font-mono); font-size: .75rem; }
    .empty, .loading { padding: var(--space-48) 0; text-align: center; color: var(--muted); }
    .confirm { border-color: var(--warning); background: color-mix(in oklch, var(--warning), white 92%); }
    .workflow-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr)); gap: var(--space-32); margin-top: var(--space-32); }
    .workflow { padding-top: var(--space-24); border-top: 1px solid var(--border); }
    .capture-workflow { grid-column: 1 / -1; }
    .workflow h3 { margin: 0 0 var(--space-8); font-size: 1.4rem; }
    .workflow form { display: grid; gap: var(--space-12); }
    .choice-list, .candidate-list { display: grid; gap: var(--space-8); margin: 0; padding: 0; list-style: none; }
    .choice, .candidate-choice { display: flex; align-items: center; gap: var(--space-8); font-weight: 500; }
    .choice input, .candidate-choice input { width: auto; }
    .candidate { width: 100%; min-height: 0; text-align: left; }
    .candidate.selected { border-color: var(--accent); background: color-mix(in oklch, var(--accent), white 94%); }
    .candidate small { display: block; margin-top: var(--space-4); color: var(--muted); }
    .selection { margin: 0; padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); }
    .selection legend { padding: 0 var(--space-4); font-family: var(--font-display); font-weight: 600; }
    .pending { color: var(--muted); background: var(--bg); }
    .selection-preview { margin: 0; padding: var(--space-8) var(--space-12); border-left: 3px solid var(--accent); color: var(--muted); }
    .capture-picker { margin-top: var(--space-24); }
    .capture-candidate { padding: var(--space-12); border: 1px solid var(--border); border-radius: var(--radius-control); }
    .capture-candidate.chosen { border-color: var(--accent); }
    .lemma { font-family: var(--font-display); font-size: 1.25rem; }
    .sense-choices { display: grid; gap: var(--space-8); margin: var(--space-12) 0 0 var(--space-24); border: 0; padding: 0; }
    .sense-choices legend { margin-bottom: var(--space-4); color: var(--muted); font-size: .8rem; }
    .language-chips { display: flex; flex-wrap: wrap; gap: var(--space-8); align-items: center; }
    .language-chips > p { width: 100%; }
    .chip.selected { color: white; border-color: var(--accent); background: var(--accent); }
    .create-actions { flex-wrap: wrap; }
    .disabled-explanation { margin: 0; color: var(--muted); font-size: .875rem; }
    .primary-nav, .bottom-nav { display: flex; gap: var(--space-8); }
    .primary-nav button[aria-current="page"], .bottom-nav button[aria-current="page"] { color: white; border-color: var(--accent); background: var(--accent); }
    .study { max-width: 760px; margin: 0 auto; }
    .study-heading { display: flex; align-items: baseline; justify-content: space-between; gap: var(--space-16); margin-bottom: var(--space-16); }
    .study-heading h2 { margin: 0; }
    .card-stage { min-height: 25rem; display: grid; align-content: center; gap: var(--space-24); padding: clamp(var(--space-24), 7vw, var(--space-72)); border: 1px solid var(--border); border-radius: var(--radius-dialog); background: var(--surface); box-shadow: var(--shadow-sm); }
    .card-stage:focus { outline: none; }
    .card-stage:focus-visible { outline: 3px solid color-mix(in oklch, var(--accent), white 65%); outline-offset: 3px; }
    .card-side { display: grid; gap: var(--space-16); }
    .front-label, .meaning-label { color: var(--muted); font-family: var(--font-mono); font-size: .75rem; letter-spacing: .08em; text-transform: uppercase; }
    .study-lemma { margin: 0; font-family: var(--font-display); font-size: clamp(3rem, 10vw, 6rem); font-weight: 600; line-height: .98; letter-spacing: -.045em; overflow-wrap: anywhere; }
    .study-meta { margin: 0; color: var(--muted); font-family: var(--font-mono); font-size: .82rem; }
    .reveal-action { justify-self: start; }
    .answer-rule { border: 0; border-top: 1px solid var(--border); width: 100%; margin: var(--space-8) 0; }
    .meaning { margin: 0; font-size: 1.25rem; }
    .example { margin: 0; padding-left: var(--space-16); border-left: 3px solid var(--accent); font-size: 1.05rem; }
    .example-translation { display: block; margin-top: var(--space-4); color: var(--muted); font-size: .9rem; }
    .pronunciation-simple { display: grid; gap: var(--space-8); }
    .extra-info-row { display: flex; flex-wrap: wrap; gap: var(--space-12); align-items: center; }
    .always-extra-toggle { display: flex; flex-direction: row; align-items: center; gap: var(--space-8); font-size: .875rem; font-weight: 500; }
    .always-extra-toggle input { width: auto; }
    .extra-info { display: grid; gap: var(--space-16); border-top: 1px solid var(--border); padding-top: var(--space-16); }
    .detail-block { margin-top: 0; }
    .detail-block p, .detail-block ul { margin-bottom: 0; }
    .detail-block ul { padding-left: var(--space-24); }
    .confidence-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: var(--space-8); }
    .confidence { min-height: 5rem; display: grid; align-content: center; justify-items: start; gap: var(--space-4); border-top: 4px solid var(--border); text-align: left; }
    .confidence:nth-child(1) { border-top-color: var(--danger); }
    .confidence:nth-child(2) { border-top-color: var(--warning); }
    .confidence:nth-child(3) { border-top-color: oklch(65% .1 95); }
    .confidence:nth-child(4) { border-top-color: oklch(62% .12 155); }
    .confidence:nth-child(5) { border-top-color: var(--accent); }
    .confidence-number { font-family: var(--font-mono); font-size: 1.1rem; }
    .confidence-text { font-size: .75rem; line-height: 1.15; }
    .study-state { min-height: 25rem; display: grid; place-content: center; text-align: center; }
    .study-state h2 { margin-bottom: var(--space-8); }
    .inline-status { margin: 0; color: var(--muted); }
    .inline-status.error { color: var(--danger); }
    .edit-meanings, .pronunciation { padding: var(--space-16); border: 1px solid var(--border); border-radius: var(--radius-panel); background: color-mix(in oklch, var(--bg), white 45%); }
    .edit-meanings h3, .pronunciation h3 { margin-bottom: var(--space-8); font-size: 1.25rem; }
    .gloss-row { display: grid; grid-template-columns: 1fr auto auto; gap: var(--space-8); align-items: end; margin-top: var(--space-12); }
    .audio-actions, .recording-actions { display: flex; flex-wrap: wrap; gap: var(--space-8); }
    .audio-preview { width: 100%; margin-top: var(--space-12); }
    .local-take { margin-top: var(--space-12); padding: var(--space-12); border: 1px dashed var(--accent); border-radius: var(--radius-control); }
    .bottom-nav { display: none; }
    @media (max-width: 800px) {
      .shell { padding: var(--space-24) var(--space-16) calc(var(--space-72) + var(--space-24)); }
      header, .form-row, .deck-heading { align-items: stretch; flex-direction: column; }
      header { align-items: flex-start; }
      header > .primary-nav { display: none; }
      .deck { grid-template-columns: 1fr; }
      .workflow-grid { grid-template-columns: 1fr; }
      .card-stage { min-height: 20rem; padding: var(--space-24); }
      .confidence-grid { grid-template-columns: 1fr; }
      .confidence { min-height: 3.6rem; grid-template-columns: 2rem 1fr; align-items: center; justify-items: start; }
      .confidence-text { font-size: .9rem; }
      .gloss-row { grid-template-columns: 1fr auto; }
      .gloss-row label { grid-column: 1 / -1; }
      .bottom-nav { position: fixed; z-index: 10; right: 0; bottom: 0; left: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 0; padding: var(--space-8) var(--space-16) calc(var(--space-8) + env(safe-area-inset-bottom)); border-top: 1px solid var(--border); background: color-mix(in oklch, var(--surface), white 12%); box-shadow: 0 -8px 24px oklch(20% .02 240 / 6%); }
      .bottom-nav button { min-height: 3rem; border: 0; background: transparent; }
    }
  `;d([h()],l.prototype,"decks",2);d([h()],l.prototype,"deckStatus",2);d([h()],l.prototype,"errorMessage",2);d([h()],l.prototype,"successMessage",2);d([h()],l.prototype,"newDeckName",2);d([h()],l.prototype,"selectedDeckId",2);d([h()],l.prototype,"pendingDeleteDeckId",2);d([h()],l.prototype,"isCreating",2);d([h()],l.prototype,"isDeleting",2);d([h()],l.prototype,"lookupQuery",2);d([h()],l.prototype,"lookupStatus",2);d([h()],l.prototype,"lookupCandidates",2);d([h()],l.prototype,"lookupAssetToken",2);d([h()],l.prototype,"selectedCandidate",2);d([h()],l.prototype,"selectedSenseRef",2);d([h()],l.prototype,"selectedMeaningLanguages",2);d([h()],l.prototype,"userMeaningDe",2);d([h()],l.prototype,"userMeaningEn",2);d([h()],l.prototype,"manualDeckId",2);d([h()],l.prototype,"isSavingNote",2);d([h()],l.prototype,"importDeckName",2);d([h()],l.prototype,"importText",2);d([h()],l.prototype,"importFileName",2);d([h()],l.prototype,"isReadingImportFile",2);d([h()],l.prototype,"isImporting",2);d([h()],l.prototype,"exportingFormat",2);d([h()],l.prototype,"captureSentence",2);d([h()],l.prototype,"captureLessonLabel",2);d([h()],l.prototype,"captureSpanStart",2);d([h()],l.prototype,"captureSpanEnd",2);d([h()],l.prototype,"captureStatus",2);d([h()],l.prototype,"captureCandidates",2);d([h()],l.prototype,"captureAssetToken",2);d([h()],l.prototype,"captureContext",2);d([h()],l.prototype,"captureSelections",2);d([h()],l.prototype,"captureMeaningLanguages",2);d([h()],l.prototype,"captureUserMeaningDe",2);d([h()],l.prototype,"captureUserMeaningEn",2);d([h()],l.prototype,"captureDeckId",2);d([h()],l.prototype,"captureError",2);d([h()],l.prototype,"captureDictionaryChanged",2);d([h()],l.prototype,"isCapturing",2);d([h()],l.prototype,"view",2);d([h()],l.prototype,"studyDeckId",2);d([h()],l.prototype,"studyStatus",2);d([h()],l.prototype,"studyCard",2);d([h()],l.prototype,"isRevealed",2);d([h()],l.prototype,"isReviewing",2);d([h()],l.prototype,"studyError",2);d([h()],l.prototype,"extraInfoOpen",2);d([h()],l.prototype,"alwaysShowExtraInfo",2);d([h()],l.prototype,"glossDrafts",2);d([h()],l.prototype,"glossState",2);d([h()],l.prototype,"glossError",2);d([h()],l.prototype,"glossSavingLanguage",2);d([h()],l.prototype,"audioStatus",2);d([h()],l.prototype,"audioMessage",2);d([h()],l.prototype,"recordingStatus",2);d([h()],l.prototype,"recordingBlob",2);d([h()],l.prototype,"recordingNoteId",2);d([h()],l.prototype,"recordingPreviewUrl",2);d([h()],l.prototype,"recordingError",2);d([h()],l.prototype,"showRecordingControls",2);d([h()],l.prototype,"revertConfirmation",2);d([h()],l.prototype,"hasCustomAudio",2);d([h()],l.prototype,"dictionaryMode",2);d([h()],l.prototype,"dictionarySettings",2);d([h()],l.prototype,"dictionarySettingsStatus",2);d([h()],l.prototype,"dictionaryAction",2);d([h()],l.prototype,"dictionaryActionMessage",2);d([h()],l.prototype,"dictionaryActionError",2);d([h()],l.prototype,"confirmRemoveOffline",2);l=d([Ne("flashcard-app")],l);
