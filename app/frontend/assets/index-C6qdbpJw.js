(function(){const e=document.createElement("link").relList;if(e&&e.supports&&e.supports("modulepreload"))return;for(const a of document.querySelectorAll('link[rel="modulepreload"]'))i(a);new MutationObserver(a=>{for(const r of a)if(r.type==="childList")for(const n of r.addedNodes)n.tagName==="LINK"&&n.rel==="modulepreload"&&i(n)}).observe(document,{childList:!0,subtree:!0});function t(a){const r={};return a.integrity&&(r.integrity=a.integrity),a.referrerPolicy&&(r.referrerPolicy=a.referrerPolicy),a.crossOrigin==="use-credentials"?r.credentials="include":a.crossOrigin==="anonymous"?r.credentials="omit":r.credentials="same-origin",r}function i(a){if(a.ep)return;a.ep=!0;const r=t(a);fetch(a.href,r)}})();/**
 * @license
 * Copyright 2019 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const F=globalThis,K=F.ShadowRoot&&(F.ShadyCSS===void 0||F.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,W=Symbol(),J=new WeakMap;let ue=class{constructor(e,t,i){if(this._$cssResult$=!0,i!==W)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=e,this.t=t}get styleSheet(){let e=this.o;const t=this.t;if(K&&e===void 0){const i=t!==void 0&&t.length===1;i&&(e=J.get(t)),e===void 0&&((this.o=e=new CSSStyleSheet).replaceSync(this.cssText),i&&J.set(t,e))}return e}toString(){return this.cssText}};const ve=s=>new ue(typeof s=="string"?s:s+"",void 0,W),ye=(s,...e)=>{const t=s.length===1?s[0]:e.reduce((i,a,r)=>i+(n=>{if(n._$cssResult$===!0)return n.cssText;if(typeof n=="number")return n;throw Error("Value passed to 'css' function must be a 'css' function result: "+n+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(a)+s[r+1],s[0]);return new ue(t,s,W)},be=(s,e)=>{if(K)s.adoptedStyleSheets=e.map(t=>t instanceof CSSStyleSheet?t:t.styleSheet);else for(const t of e){const i=document.createElement("style"),a=F.litNonce;a!==void 0&&i.setAttribute("nonce",a),i.textContent=t.cssText,s.appendChild(i)}},Z=K?s=>s:s=>s instanceof CSSStyleSheet?(e=>{let t="";for(const i of e.cssRules)t+=i.cssText;return ve(t)})(s):s;/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const{is:$e,defineProperty:ke,getOwnPropertyDescriptor:we,getOwnPropertyNames:Se,getOwnPropertySymbols:_e,getPrototypeOf:Ce}=Object,k=globalThis,X=k.trustedTypes,xe=X?X.emptyScript:"",q=k.reactiveElementPolyfillSupport,D=(s,e)=>s,G={toAttribute(s,e){switch(e){case Boolean:s=s?xe:null;break;case Object:case Array:s=s==null?s:JSON.stringify(s)}return s},fromAttribute(s,e){let t=s;switch(e){case Boolean:t=s!==null;break;case Number:t=s===null?null:Number(s);break;case Object:case Array:try{t=JSON.parse(s)}catch{t=null}}return t}},Y=(s,e)=>!$e(s,e),ee={attribute:!0,type:String,converter:G,reflect:!1,useDefault:!1,hasChanged:Y};Symbol.metadata??(Symbol.metadata=Symbol("metadata")),k.litPropertyMetadata??(k.litPropertyMetadata=new WeakMap);let x=class extends HTMLElement{static addInitializer(e){this._$Ei(),(this.l??(this.l=[])).push(e)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(e,t=ee){if(t.state&&(t.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(e)&&((t=Object.create(t)).wrapped=!0),this.elementProperties.set(e,t),!t.noAccessor){const i=Symbol(),a=this.getPropertyDescriptor(e,i,t);a!==void 0&&ke(this.prototype,e,a)}}static getPropertyDescriptor(e,t,i){const{get:a,set:r}=we(this.prototype,e)??{get(){return this[t]},set(n){this[t]=n}};return{get:a,set(n){const h=a==null?void 0:a.call(this);r==null||r.call(this,n),this.requestUpdate(e,h,i)},configurable:!0,enumerable:!0}}static getPropertyOptions(e){return this.elementProperties.get(e)??ee}static _$Ei(){if(this.hasOwnProperty(D("elementProperties")))return;const e=Ce(this);e.finalize(),e.l!==void 0&&(this.l=[...e.l]),this.elementProperties=new Map(e.elementProperties)}static finalize(){if(this.hasOwnProperty(D("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(D("properties"))){const t=this.properties,i=[...Se(t),..._e(t)];for(const a of i)this.createProperty(a,t[a])}const e=this[Symbol.metadata];if(e!==null){const t=litPropertyMetadata.get(e);if(t!==void 0)for(const[i,a]of t)this.elementProperties.set(i,a)}this._$Eh=new Map;for(const[t,i]of this.elementProperties){const a=this._$Eu(t,i);a!==void 0&&this._$Eh.set(a,t)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(e){const t=[];if(Array.isArray(e)){const i=new Set(e.flat(1/0).reverse());for(const a of i)t.unshift(Z(a))}else e!==void 0&&t.push(Z(e));return t}static _$Eu(e,t){const i=t.attribute;return i===!1?void 0:typeof i=="string"?i:typeof e=="string"?e.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){var e;this._$ES=new Promise(t=>this.enableUpdating=t),this._$AL=new Map,this._$E_(),this.requestUpdate(),(e=this.constructor.l)==null||e.forEach(t=>t(this))}addController(e){var t;(this._$EO??(this._$EO=new Set)).add(e),this.renderRoot!==void 0&&this.isConnected&&((t=e.hostConnected)==null||t.call(e))}removeController(e){var t;(t=this._$EO)==null||t.delete(e)}_$E_(){const e=new Map,t=this.constructor.elementProperties;for(const i of t.keys())this.hasOwnProperty(i)&&(e.set(i,this[i]),delete this[i]);e.size>0&&(this._$Ep=e)}createRenderRoot(){const e=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return be(e,this.constructor.elementStyles),e}connectedCallback(){var e;this.renderRoot??(this.renderRoot=this.createRenderRoot()),this.enableUpdating(!0),(e=this._$EO)==null||e.forEach(t=>{var i;return(i=t.hostConnected)==null?void 0:i.call(t)})}enableUpdating(e){}disconnectedCallback(){var e;(e=this._$EO)==null||e.forEach(t=>{var i;return(i=t.hostDisconnected)==null?void 0:i.call(t)})}attributeChangedCallback(e,t,i){this._$AK(e,i)}_$ET(e,t){var r;const i=this.constructor.elementProperties.get(e),a=this.constructor._$Eu(e,i);if(a!==void 0&&i.reflect===!0){const n=(((r=i.converter)==null?void 0:r.toAttribute)!==void 0?i.converter:G).toAttribute(t,i.type);this._$Em=e,n==null?this.removeAttribute(a):this.setAttribute(a,n),this._$Em=null}}_$AK(e,t){var r,n;const i=this.constructor,a=i._$Eh.get(e);if(a!==void 0&&this._$Em!==a){const h=i.getPropertyOptions(a),c=typeof h.converter=="function"?{fromAttribute:h.converter}:((r=h.converter)==null?void 0:r.fromAttribute)!==void 0?h.converter:G;this._$Em=a;const g=c.fromAttribute(t,h.type);this[a]=g??((n=this._$Ej)==null?void 0:n.get(a))??g,this._$Em=null}}requestUpdate(e,t,i,a=!1,r){var n;if(e!==void 0){const h=this.constructor;if(a===!1&&(r=this[e]),i??(i=h.getPropertyOptions(e)),!((i.hasChanged??Y)(r,t)||i.useDefault&&i.reflect&&r===((n=this._$Ej)==null?void 0:n.get(e))&&!this.hasAttribute(h._$Eu(e,i))))return;this.C(e,t,i)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(e,t,{useDefault:i,reflect:a,wrapped:r},n){i&&!(this._$Ej??(this._$Ej=new Map)).has(e)&&(this._$Ej.set(e,n??t??this[e]),r!==!0||n!==void 0)||(this._$AL.has(e)||(this.hasUpdated||i||(t=void 0),this._$AL.set(e,t)),a===!0&&this._$Em!==e&&(this._$Eq??(this._$Eq=new Set)).add(e))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(t){Promise.reject(t)}const e=this.scheduleUpdate();return e!=null&&await e,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){var i;if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??(this.renderRoot=this.createRenderRoot()),this._$Ep){for(const[r,n]of this._$Ep)this[r]=n;this._$Ep=void 0}const a=this.constructor.elementProperties;if(a.size>0)for(const[r,n]of a){const{wrapped:h}=n,c=this[r];h!==!0||this._$AL.has(r)||c===void 0||this.C(r,void 0,n,c)}}let e=!1;const t=this._$AL;try{e=this.shouldUpdate(t),e?(this.willUpdate(t),(i=this._$EO)==null||i.forEach(a=>{var r;return(r=a.hostUpdate)==null?void 0:r.call(a)}),this.update(t)):this._$EM()}catch(a){throw e=!1,this._$EM(),a}e&&this._$AE(t)}willUpdate(e){}_$AE(e){var t;(t=this._$EO)==null||t.forEach(i=>{var a;return(a=i.hostUpdated)==null?void 0:a.call(i)}),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(e)),this.updated(e)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(e){return!0}update(e){this._$Eq&&(this._$Eq=this._$Eq.forEach(t=>this._$ET(t,this[t]))),this._$EM()}updated(e){}firstUpdated(e){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[D("elementProperties")]=new Map,x[D("finalized")]=new Map,q==null||q({ReactiveElement:x}),(k.reactiveElementVersions??(k.reactiveElementVersions=[])).push("2.1.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const R=globalThis,te=s=>s,j=R.trustedTypes,se=j?j.createPolicy("lit-html",{createHTML:s=>s}):void 0,he="$lit$",$=`lit$${Math.random().toFixed(9).slice(2)}$`,pe="?"+$,Ee=`<${pe}>`,C=document,I=()=>C.createComment(""),P=s=>s===null||typeof s!="object"&&typeof s!="function",Q=Array.isArray,Ae=s=>Q(s)||typeof(s==null?void 0:s[Symbol.iterator])=="function",H=`[ 	
\f\r]`,M=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,ie=/-->/g,ae=/>/g,w=RegExp(`>|${H}(?:([^\\s"'>=/]+)(${H}*=${H}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),re=/'/g,ne=/"/g,ge=/^(?:script|style|textarea|title)$/i,Me=s=>(e,...t)=>({_$litType$:s,strings:e,values:t}),o=Me(1),E=Symbol.for("lit-noChange"),p=Symbol.for("lit-nothing"),oe=new WeakMap,S=C.createTreeWalker(C,129);function me(s,e){if(!Q(s)||!s.hasOwnProperty("raw"))throw Error("invalid template strings array");return se!==void 0?se.createHTML(e):e}const De=(s,e)=>{const t=s.length-1,i=[];let a,r=e===2?"<svg>":e===3?"<math>":"",n=M;for(let h=0;h<t;h++){const c=s[h];let g,f,m=-1,y=0;for(;y<c.length&&(n.lastIndex=y,f=n.exec(c),f!==null);)y=n.lastIndex,n===M?f[1]==="!--"?n=ie:f[1]!==void 0?n=ae:f[2]!==void 0?(ge.test(f[2])&&(a=RegExp("</"+f[2],"g")),n=w):f[3]!==void 0&&(n=w):n===w?f[0]===">"?(n=a??M,m=-1):f[1]===void 0?m=-2:(m=n.lastIndex-f[2].length,g=f[1],n=f[3]===void 0?w:f[3]==='"'?ne:re):n===ne||n===re?n=w:n===ie||n===ae?n=M:(n=w,a=void 0);const b=n===w&&s[h+1].startsWith("/>")?" ":"";r+=n===M?c+Ee:m>=0?(i.push(g),c.slice(0,m)+he+c.slice(m)+$+b):c+$+(m===-2?h:b)}return[me(s,r+(s[t]||"<?>")+(e===2?"</svg>":e===3?"</math>":"")),i]};class L{constructor({strings:e,_$litType$:t},i){let a;this.parts=[];let r=0,n=0;const h=e.length-1,c=this.parts,[g,f]=De(e,t);if(this.el=L.createElement(g,i),S.currentNode=this.el.content,t===2||t===3){const m=this.el.content.firstChild;m.replaceWith(...m.childNodes)}for(;(a=S.nextNode())!==null&&c.length<h;){if(a.nodeType===1){if(a.hasAttributes())for(const m of a.getAttributeNames())if(m.endsWith(he)){const y=f[n++],b=a.getAttribute(m).split($),U=/([.?@])?(.*)/.exec(y);c.push({type:1,index:r,name:U[2],strings:b,ctor:U[1]==="."?Te:U[1]==="?"?Ie:U[1]==="@"?Pe:z}),a.removeAttribute(m)}else m.startsWith($)&&(c.push({type:6,index:r}),a.removeAttribute(m));if(ge.test(a.tagName)){const m=a.textContent.split($),y=m.length-1;if(y>0){a.textContent=j?j.emptyScript:"";for(let b=0;b<y;b++)a.append(m[b],I()),S.nextNode(),c.push({type:2,index:++r});a.append(m[y],I())}}}else if(a.nodeType===8)if(a.data===pe)c.push({type:2,index:r});else{let m=-1;for(;(m=a.data.indexOf($,m+1))!==-1;)c.push({type:7,index:r}),m+=$.length-1}r++}}static createElement(e,t){const i=C.createElement("template");return i.innerHTML=e,i}}function A(s,e,t=s,i){var n,h;if(e===E)return e;let a=i!==void 0?(n=t._$Co)==null?void 0:n[i]:t._$Cl;const r=P(e)?void 0:e._$litDirective$;return(a==null?void 0:a.constructor)!==r&&((h=a==null?void 0:a._$AO)==null||h.call(a,!1),r===void 0?a=void 0:(a=new r(s),a._$AT(s,t,i)),i!==void 0?(t._$Co??(t._$Co=[]))[i]=a:t._$Cl=a),a!==void 0&&(e=A(s,a._$AS(s,e.values),a,i)),e}class Re{constructor(e,t){this._$AV=[],this._$AN=void 0,this._$AD=e,this._$AM=t}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(e){const{el:{content:t},parts:i}=this._$AD,a=((e==null?void 0:e.creationScope)??C).importNode(t,!0);S.currentNode=a;let r=S.nextNode(),n=0,h=0,c=i[0];for(;c!==void 0;){if(n===c.index){let g;c.type===2?g=new O(r,r.nextSibling,this,e):c.type===1?g=new c.ctor(r,c.name,c.strings,this,e):c.type===6&&(g=new Le(r,this,e)),this._$AV.push(g),c=i[++h]}n!==(c==null?void 0:c.index)&&(r=S.nextNode(),n++)}return S.currentNode=C,a}p(e){let t=0;for(const i of this._$AV)i!==void 0&&(i.strings!==void 0?(i._$AI(e,i,t),t+=i.strings.length-2):i._$AI(e[t])),t++}}class O{get _$AU(){var e;return((e=this._$AM)==null?void 0:e._$AU)??this._$Cv}constructor(e,t,i,a){this.type=2,this._$AH=p,this._$AN=void 0,this._$AA=e,this._$AB=t,this._$AM=i,this.options=a,this._$Cv=(a==null?void 0:a.isConnected)??!0}get parentNode(){let e=this._$AA.parentNode;const t=this._$AM;return t!==void 0&&(e==null?void 0:e.nodeType)===11&&(e=t.parentNode),e}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(e,t=this){e=A(this,e,t),P(e)?e===p||e==null||e===""?(this._$AH!==p&&this._$AR(),this._$AH=p):e!==this._$AH&&e!==E&&this._(e):e._$litType$!==void 0?this.$(e):e.nodeType!==void 0?this.T(e):Ae(e)?this.k(e):this._(e)}O(e){return this._$AA.parentNode.insertBefore(e,this._$AB)}T(e){this._$AH!==e&&(this._$AR(),this._$AH=this.O(e))}_(e){this._$AH!==p&&P(this._$AH)?this._$AA.nextSibling.data=e:this.T(C.createTextNode(e)),this._$AH=e}$(e){var r;const{values:t,_$litType$:i}=e,a=typeof i=="number"?this._$AC(e):(i.el===void 0&&(i.el=L.createElement(me(i.h,i.h[0]),this.options)),i);if(((r=this._$AH)==null?void 0:r._$AD)===a)this._$AH.p(t);else{const n=new Re(a,this),h=n.u(this.options);n.p(t),this.T(h),this._$AH=n}}_$AC(e){let t=oe.get(e.strings);return t===void 0&&oe.set(e.strings,t=new L(e)),t}k(e){Q(this._$AH)||(this._$AH=[],this._$AR());const t=this._$AH;let i,a=0;for(const r of e)a===t.length?t.push(i=new O(this.O(I()),this.O(I()),this,this.options)):i=t[a],i._$AI(r),a++;a<t.length&&(this._$AR(i&&i._$AB.nextSibling,a),t.length=a)}_$AR(e=this._$AA.nextSibling,t){var i;for((i=this._$AP)==null?void 0:i.call(this,!1,!0,t);e!==this._$AB;){const a=te(e).nextSibling;te(e).remove(),e=a}}setConnected(e){var t;this._$AM===void 0&&(this._$Cv=e,(t=this._$AP)==null||t.call(this,e))}}class z{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(e,t,i,a,r){this.type=1,this._$AH=p,this._$AN=void 0,this.element=e,this.name=t,this._$AM=a,this.options=r,i.length>2||i[0]!==""||i[1]!==""?(this._$AH=Array(i.length-1).fill(new String),this.strings=i):this._$AH=p}_$AI(e,t=this,i,a){const r=this.strings;let n=!1;if(r===void 0)e=A(this,e,t,0),n=!P(e)||e!==this._$AH&&e!==E,n&&(this._$AH=e);else{const h=e;let c,g;for(e=r[0],c=0;c<r.length-1;c++)g=A(this,h[i+c],t,c),g===E&&(g=this._$AH[c]),n||(n=!P(g)||g!==this._$AH[c]),g===p?e=p:e!==p&&(e+=(g??"")+r[c+1]),this._$AH[c]=g}n&&!a&&this.j(e)}j(e){e===p?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,e??"")}}class Te extends z{constructor(){super(...arguments),this.type=3}j(e){this.element[this.name]=e===p?void 0:e}}class Ie extends z{constructor(){super(...arguments),this.type=4}j(e){this.element.toggleAttribute(this.name,!!e&&e!==p)}}class Pe extends z{constructor(e,t,i,a,r){super(e,t,i,a,r),this.type=5}_$AI(e,t=this){if((e=A(this,e,t,0)??p)===E)return;const i=this._$AH,a=e===p&&i!==p||e.capture!==i.capture||e.once!==i.once||e.passive!==i.passive,r=e!==p&&(i===p||a);a&&this.element.removeEventListener(this.name,this,i),r&&this.element.addEventListener(this.name,this,e),this._$AH=e}handleEvent(e){var t;typeof this._$AH=="function"?this._$AH.call(((t=this.options)==null?void 0:t.host)??this.element,e):this._$AH.handleEvent(e)}}class Le{constructor(e,t,i){this.element=e,this.type=6,this._$AN=void 0,this._$AM=t,this.options=i}get _$AU(){return this._$AM._$AU}_$AI(e){A(this,e)}}const B=R.litHtmlPolyfillSupport;B==null||B(L,O),(R.litHtmlVersions??(R.litHtmlVersions=[])).push("3.3.3");const Ne=(s,e,t)=>{const i=(t==null?void 0:t.renderBefore)??e;let a=i._$litPart$;if(a===void 0){const r=(t==null?void 0:t.renderBefore)??null;i._$litPart$=a=new O(e.insertBefore(I(),r),r,void 0,t??{})}return a._$AI(s),a};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const _=globalThis;class T extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){var t;const e=super.createRenderRoot();return(t=this.renderOptions).renderBefore??(t.renderBefore=e.firstChild),e}update(e){const t=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(e),this._$Do=Ne(t,this.renderRoot,this.renderOptions)}connectedCallback(){var e;super.connectedCallback(),(e=this._$Do)==null||e.setConnected(!0)}disconnectedCallback(){var e;super.disconnectedCallback(),(e=this._$Do)==null||e.setConnected(!1)}render(){return E}}var de;T._$litElement$=!0,T.finalized=!0,(de=_.litElementHydrateSupport)==null||de.call(_,{LitElement:T});const V=_.litElementPolyfillSupport;V==null||V({LitElement:T});(_.litElementVersions??(_.litElementVersions=[])).push("4.2.2");/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Oe=s=>(e,t)=>{t!==void 0?t.addInitializer(()=>{customElements.define(s,e)}):customElements.define(s,e)};/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */const Ue={attribute:!0,type:String,converter:G,reflect:!1,hasChanged:Y},Fe=(s=Ue,e,t)=>{const{kind:i,metadata:a}=t;let r=globalThis.litPropertyMetadata.get(a);if(r===void 0&&globalThis.litPropertyMetadata.set(a,r=new Map),i==="setter"&&((s=Object.create(s)).wrapped=!0),r.set(t.name,s),i==="accessor"){const{name:n}=t;return{set(h){const c=e.get.call(this);e.set.call(this,h),this.requestUpdate(n,c,s,!0,h)},init(h){return h!==void 0&&this.C(n,void 0,s,h),h}}}if(i==="setter"){const{name:n}=t;return function(h){const c=this[n];e.call(this,h),this.requestUpdate(n,c,s,!0,h)}}throw Error("Unsupported decorator location: "+i)};function Ge(s){return(e,t)=>typeof t=="object"?Fe(s,e,t):((i,a,r)=>{const n=a.hasOwnProperty(r);return a.constructor.createProperty(r,i),n?Object.getOwnPropertyDescriptor(a,r):void 0})(s,e,t)}/**
 * @license
 * Copyright 2017 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */function u(s){return Ge({...s,state:!0,attribute:!1})}class N extends Error{constructor(e,t,i,a,r,n){const h=a||`API request failed with status ${e} (${t})`;super(h),this.name="ApiError",this.status=e,this.statusText=t,this.body=i,this.detail=a,this.pickerToken=r,this.activeToken=n,Object.setPrototypeOf(this,N.prototype)}get isConflict(){return this.status===409}get isNotFound(){return this.status===404}get isUnprocessable(){return this.status===422}get isForbidden(){return this.status===403}get isBadRequest(){return this.status===400}}async function je(s){const e=s.status,t=s.statusText;let i=null,a,r,n;try{if((s.headers.get("content-type")||"").includes("application/json")){const c=await s.json();i=c,typeof c.detail=="string"?a=c.detail:Array.isArray(c.detail)&&c.detail.length>0&&(a=c.detail.map(g=>g.msg||JSON.stringify(g)).join("; ")),typeof c.picker_token=="string"&&(r=c.picker_token),typeof c.active_token=="string"&&(n=c.active_token)}else{const c=await s.text();i=c,a=c||void 0}}catch{}return new N(e,t,i,a,r,n)}class ze{constructor(e={}){this.baseUrl=e.baseUrl?e.baseUrl.replace(/\/+$/,""):"",this._fetch=e.fetch??globalThis.fetch.bind(globalThis)}async request(e,t={}){const i=t.method??"GET",a=i==="GET";let r=`${this.baseUrl}${e.startsWith("/")?e:`/${e}`}`;if(t.params){const g=new URLSearchParams;for(const[m,y]of Object.entries(t.params))y!=null&&g.append(m,String(y));const f=g.toString();f&&(r+=(r.includes("?")?"&":"?")+f)}const n={...t.headers};a||(n["X-Flashcards-Request"]="1");let h;t.body!==void 0&&t.body!==null&&(t.body instanceof FormData||t.body instanceof Blob||t.body instanceof ArrayBuffer||ArrayBuffer.isView(t.body)?h=t.body:(n["Content-Type"]="application/json",h=JSON.stringify(t.body)));const c=await this._fetch(r,{method:i,headers:n,body:h});if(!c.ok)throw await je(c);if(t.responseType==="text")return await c.text();if(t.responseType==="blob")return await c.blob();if(!(c.status===204||c.headers.get("content-length")==="0"))return await c.json()}async lookup(e){return this.request("/vocab/lookup",{method:"GET",params:{q:e}})}async lookupPost(e){return this.request("/vocab/lookup",{method:"POST",body:{query:e}})}async activateDictionary(e){return this.request("/vocab/dictionary/activate",{method:"POST",body:e})}async highlight(e){return this.request("/vocab/highlight",{method:"POST",body:e})}async captureCards(e){return this.request("/vocab/cards",{method:"POST",body:e})}async importCsv(e){return this.request("/vocab/import/csv",{method:"POST",body:e})}async createNote(e){return this.request("/vocab/notes",{method:"POST",body:e})}async getNextCard(e){return this.request("/vocab/cards/next",{method:"GET",params:{deck_id:e}})}async reviewCard(e,t){return this.request(`/vocab/cards/${e}/review`,{method:"POST",body:{confidence:t}})}async setGloss(e,t,i){return this.request(`/vocab/notes/${e}/gloss`,{method:"POST",body:{language:t,meaning_text:i}})}async deleteGloss(e,t){return this.request(`/vocab/notes/${e}/gloss`,{method:"DELETE",params:{language:t}})}async uploadAudio(e,t,i){const a={};return i&&!(t instanceof FormData)&&(a["Content-Type"]=i),this.request(`/vocab/notes/${e}/audio`,{method:"POST",body:t,headers:a})}async revertAudio(e){return this.request(`/vocab/notes/${e}/audio`,{method:"DELETE"})}getAudioUrl(e){const t=encodeURIComponent(String(e));return`${this.baseUrl}/vocab/audio/${t}`}async fetchAudio(e){const t=encodeURIComponent(String(e));return this.request(`/vocab/audio/${t}`,{method:"GET",responseType:"blob"})}async getDecks(){return this.request("/vocab/decks",{method:"GET"})}async createDeck(e){const t={name:e};return this.request("/vocab/decks",{method:"POST",body:t})}async deleteDeck(e){return this.request(`/vocab/decks/${e}`,{method:"DELETE"})}async exportAnki(e){return this.request("/vocab/export/anki",{method:"GET",params:{deck_id:e},responseType:"text"})}async exportApkg(e){return this.request("/vocab/export/apkg",{method:"GET",params:{deck_id:e},responseType:"blob"})}}function qe(s){return new ze(s)}const fe="wortlaut.study.alwaysShowExtraInfo";function He(s){if(!s)return!1;try{return s.getItem(fe)==="true"}catch{return!1}}function Be(s,e){if(s)try{s.setItem(fe,e?"true":"false")}catch{}}function ce(){return!1}function Ve(s){return s.isRevealed?s.newPreference:!1}var Ke=Object.defineProperty,We=Object.getOwnPropertyDescriptor,d=(s,e,t,i)=>{for(var a=i>1?void 0:i?We(e,t):e,r=s.length-1,n;r>=0;r--)(n=s[r])&&(a=(i?n(e,t,a):n(a))||a);return i&&a&&Ke(e,t,a),a};const Ye=[["1","Not at all"],["2","Barely"],["3","With effort"],["4","Comfortably"],["5","Without doubt"]],v=qe();function le(){try{return window.localStorage}catch{return null}}let l=class extends T{constructor(){super(...arguments),this.decks=[],this.deckStatus="loading",this.errorMessage="",this.successMessage="",this.newDeckName="",this.selectedDeckId=null,this.pendingDeleteDeckId=null,this.isCreating=!1,this.isDeleting=!1,this.lookupQuery="",this.lookupStatus="idle",this.lookupCandidates=[],this.lookupAssetToken="",this.selectedCandidate=null,this.selectedSenseRef=null,this.selectedMeaningLanguages=["de","en"],this.userMeaningDe="",this.userMeaningEn="",this.manualDeckId=null,this.isSavingNote=!1,this.importDeckName="",this.importText="",this.importFileName="",this.isReadingImportFile=!1,this.isImporting=!1,this.exportingFormat=null,this.captureSentence="",this.captureLessonLabel="",this.captureSpanStart=0,this.captureSpanEnd=0,this.captureStatus="idle",this.captureCandidates=[],this.captureAssetToken="",this.captureContext=null,this.captureSelections={},this.captureMeaningLanguages=["de","en"],this.captureUserMeaningDe="",this.captureUserMeaningEn="",this.captureDeckId=null,this.captureError="",this.captureDictionaryChanged=!1,this.isCapturing=!1,this.view="decks",this.studyDeckId=null,this.studyStatus="idle",this.studyCard=null,this.isRevealed=!1,this.isReviewing=!1,this.studyError="",this.extraInfoOpen=!1,this.alwaysShowExtraInfo=He(le()),this.glossDrafts={de:"",en:""},this.glossState="",this.glossError="",this.glossSavingLanguage=null,this.audioStatus="idle",this.audioMessage="",this.recordingStatus="idle",this.recordingBlob=null,this.recordingNoteId=null,this.recordingPreviewUrl="",this.recordingError="",this.showRecordingControls=!1,this.revertConfirmation=!1,this.hasCustomAudio=!1,this.focusTarget=null,this.audioPlayer=null,this.mediaRecorder=null,this.recordingChunks=[],this.handleStudyKeydown=s=>{if(this.view!=="study")return;const e=s.target;if(!(e!=null&&e.closest('input, textarea, select, [contenteditable="true"]'))){if(s.code==="Space"&&!this.isRevealed){s.preventDefault(),this.revealCard();return}if(s.key>="1"&&s.key<="5"&&this.isRevealed){s.preventDefault(),this.submitConfidence(Number(s.key));return}s.key.toLowerCase()==="r"&&(s.preventDefault(),this.playPronunciation())}}}connectedCallback(){super.connectedCallback(),this.loadDecks(),window.addEventListener("keydown",this.handleStudyKeydown)}disconnectedCallback(){window.removeEventListener("keydown",this.handleStudyKeydown),this.stopAudio(),this.releaseRecordingPreview(),super.disconnectedCallback()}updated(){if(!this.focusTarget)return;const s=this.focusTarget==="answer"?"[data-study-answer]":"[data-study-empty]",e=this.renderRoot.querySelector(s);e&&(e.focus(),this.focusTarget=null)}async loadDecks(){this.deckStatus="loading",this.errorMessage="",this.successMessage="";try{const s=await v.getDecks();return this.decks=s,this.selectedDeckId!==null&&!s.some(e=>e.id===this.selectedDeckId)&&(this.selectedDeckId=null),this.manualDeckId!==null&&!s.some(e=>e.id===this.manualDeckId)&&(this.manualDeckId=null),this.captureDeckId!==null&&!s.some(e=>e.id===this.captureDeckId)&&(this.captureDeckId=null),this.deckStatus="ready",s}catch(s){return this.deckStatus="error",this.errorMessage=this.messageFor(s,"Decks could not be loaded."),null}}async createDeck(s){s.preventDefault();const e=this.newDeckName.trim();if(!e){this.successMessage="",this.errorMessage="Enter a deck name before creating it.";return}this.isCreating=!0,this.errorMessage="",this.successMessage="";try{const t=await v.createDeck(e);this.newDeckName="";const i=await this.loadDecks();if(i===null){this.errorMessage=`“${t.name}” may have been created, but the deck list could not be refreshed.`;return}const a=i.find(r=>r.id===t.id);if(!a){this.errorMessage=`The server did not return “${t.name}” after creation. It was not opened.`;return}this.selectedDeckId=a.id,this.manualDeckId=a.id,this.captureDeckId=a.id,this.importDeckName=a.name,this.successMessage=`Created and opened “${a.name}”.`}catch(t){this.successMessage="",this.errorMessage=this.messageFor(t,"Deck could not be created.")}finally{this.isCreating=!1}}async deleteDeck(s){this.isDeleting=!0,this.errorMessage="",this.successMessage="";try{if(!(await v.deleteDeck(s.id)).deleted)throw new Error("The server did not confirm deletion.");this.pendingDeleteDeckId=null;const t=await this.loadDecks();if(t===null){this.errorMessage=`“${s.name}” may have been deleted, but the deck list could not be refreshed.`;return}if(t.some(i=>i.id===s.id)){this.errorMessage=`The server still returned “${s.name}” after deletion. The deletion was not confirmed.`;return}this.selectedDeckId===s.id&&(this.selectedDeckId=null),this.successMessage=`Deleted “${s.name}”. Notes with review history were preserved by the server.`}catch(e){this.successMessage="",this.errorMessage=this.messageFor(e,"Deck could not be deleted.")}finally{this.isDeleting=!1}}messageFor(s,e){return s instanceof N&&s.detail?s.detail:s instanceof Error&&s.message?s.message:e}openDeck(s){this.selectedDeckId=s.id,this.manualDeckId=s.id,this.captureDeckId=s.id,this.importDeckName=s.name,this.view="deck",this.successMessage=""}async openStudy(s){if(this.recordingBlob||this.recordingStatus==="recording"){this.view="study",this.errorMessage="Save or discard the local recording before changing study sessions.";return}this.view="study",this.studyDeckId=s??null,this.studyCard=null,this.isRevealed=!1,this.extraInfoOpen=ce(),this.studyError="",this.clearPronunciationState(),await this.loadStudyCard()}clearPronunciationState(){this.stopAudio(),this.audioMessage="",this.audioStatus="idle",this.showRecordingControls=!1,this.revertConfirmation=!1}async loadStudyCard(){var s,e;this.studyStatus="loading",this.studyError="";try{const t=await v.getNextCard(this.studyDeckId??void 0);this.studyCard=t.card,this.isRevealed=!1,this.extraInfoOpen=ce(),this.hasCustomAudio=!!((e=(s=t.card)==null?void 0:s.front.audio_trigger.token)!=null&&e.startsWith("custom:")),this.glossDrafts={de:this.userGlossValue(t.card,"de"),en:this.userGlossValue(t.card,"en")},this.glossState="",this.glossError="",this.studyStatus=t.card?"ready":"empty",t.card||(this.focusTarget="empty")}catch(t){this.studyCard=null,this.studyStatus="error",this.studyError=this.messageFor(t,"The next card could not be loaded.")}}revealCard(){!this.studyCard||this.isRevealed||this.isReviewing||(this.isRevealed=!0,this.extraInfoOpen=this.alwaysShowExtraInfo,this.focusTarget="answer")}toggleExtraInfo(){this.extraInfoOpen=!this.extraInfoOpen}setAlwaysShowExtraInfo(s){this.alwaysShowExtraInfo=s,Be(le(),s),this.extraInfoOpen=Ve({isRevealed:this.isRevealed,newPreference:s})}async submitConfidence(s){const e=this.studyCard;if(!(!e||!this.isRevealed||this.isReviewing)){if(this.recordingBlob){this.studyError="Save or discard the local recording before continuing to the next card.";return}this.isReviewing=!0,this.studyError="";try{await v.reviewCard(e.card_id,s),await this.loadStudyCard()}catch(t){this.studyError=this.messageFor(t,"Your confidence could not be saved. Try the same rating again.")}finally{this.isReviewing=!1}}}meaningFor(s,e){return s==null?void 0:s.back.meanings.find(t=>t.language===e)}userGlossValue(s,e){const t=this.meaningFor(s,e);return t!=null&&t.is_user_authored?t.lines.join(" "):""}async saveGloss(s){const e=this.studyCard,t=this.glossDrafts[s].trim();if(!(!e||!t)){this.glossSavingLanguage=s,this.glossError="",this.glossState="";try{const i=await v.setGloss(e.note_id,s,t);this.glossDrafts={...this.glossDrafts,[s]:i.meaning_text},this.glossState=`${s==="de"?"German":"English"} meaning saved.`,await this.refreshStudyFace(e.card_id)}catch(i){this.glossError=this.messageFor(i,"That meaning could not be saved.")}finally{this.glossSavingLanguage=null}}}async deleteGloss(s){const e=this.studyCard;if(e){this.glossSavingLanguage=s,this.glossError="",this.glossState="";try{if(!(await v.deleteGloss(e.note_id,s)).deleted)throw new Error("The server did not confirm removal.");this.glossDrafts={...this.glossDrafts,[s]:""},this.glossState=`${s==="de"?"German":"English"} meaning removed.`,await this.refreshStudyFace(e.card_id)}catch(t){this.glossError=this.messageFor(t,"That meaning could not be removed.")}finally{this.glossSavingLanguage=null}}}async refreshStudyFace(s){var e,t;try{const i=await v.getNextCard(this.studyDeckId??void 0);((e=i.card)==null?void 0:e.card_id)===s&&(this.studyCard=i.card,this.hasCustomAudio=!!((t=i.card.front.audio_trigger.token)!=null&&t.startsWith("custom:")))}catch{}}audioRequestId(s){return this.hasCustomAudio?s.note_id:s.front.audio_trigger.lemma}stopAudio(){this.audioPlayer&&(this.audioPlayer.pause(),this.audioPlayer.src="",this.audioPlayer=null),this.audioStatus==="playing"&&(this.audioStatus="idle")}async playPronunciation(){const s=this.studyCard;if(!(!s||!s.front.audio_trigger.available||this.audioStatus==="loading")){this.stopAudio(),this.audioStatus="loading",this.audioMessage="Loading pronunciation…";try{const e=await v.fetchAudio(this.audioRequestId(s)),t=URL.createObjectURL(e),i=new Audio(t);this.audioPlayer=i,i.onended=()=>{URL.revokeObjectURL(t),this.audioPlayer=null,this.audioStatus="idle",this.audioMessage=""},await i.play(),this.audioStatus="playing",this.audioMessage="Playing pronunciation…"}catch(e){this.audioStatus="unavailable",this.audioMessage=this.messageFor(e,"Pronunciation is unavailable right now.")}}}releaseRecordingPreview(){this.recordingPreviewUrl&&URL.revokeObjectURL(this.recordingPreviewUrl),this.recordingPreviewUrl=""}setLocalRecording(s){var e;this.releaseRecordingPreview(),this.recordingBlob=s,this.recordingNoteId=((e=this.studyCard)==null?void 0:e.note_id)??null,this.recordingPreviewUrl=URL.createObjectURL(s),this.recordingStatus="ready",this.recordingError=""}async startRecording(){var s;if(!((s=navigator.mediaDevices)!=null&&s.getUserMedia)||typeof MediaRecorder>"u"){this.recordingError="Recording is not available in this browser. You can choose an audio file instead.";return}try{const e=await navigator.mediaDevices.getUserMedia({audio:!0}),t=new MediaRecorder(e);this.recordingChunks=[],t.ondataavailable=i=>{i.data.size&&this.recordingChunks.push(i.data)},t.onstop=()=>{e.getTracks().forEach(i=>i.stop()),this.setLocalRecording(new Blob(this.recordingChunks,{type:t.mimeType||"audio/webm"}))},t.start(),this.mediaRecorder=t,this.recordingStatus="recording",this.recordingError=""}catch(e){this.recordingError=this.messageFor(e,"Microphone access was not granted. You can choose an audio file instead.")}}stopRecording(){var s;((s=this.mediaRecorder)==null?void 0:s.state)==="recording"&&this.mediaRecorder.stop(),this.mediaRecorder=null}selectAudioFile(s){var t;const e=(t=s.target.files)==null?void 0:t[0];e&&this.setLocalRecording(e)}discardRecording(){this.releaseRecordingPreview(),this.recordingBlob=null,this.recordingNoteId=null,this.recordingStatus="idle",this.recordingError=""}async saveRecording(){const s=this.studyCard,e=this.recordingBlob;if(!(!s||!e||this.recordingNoteId!==s.note_id)){this.recordingStatus="saving",this.recordingError="";try{await v.uploadAudio(s.note_id,e,e.type||"audio/webm"),this.discardRecording(),this.showRecordingControls=!1,this.hasCustomAudio=!0,this.audioMessage="Custom pronunciation saved.",await this.refreshStudyFace(s.card_id)}catch(t){this.recordingStatus="save-error",this.recordingError=this.messageFor(t,"The recording was not saved. Your local take is still available.")}}}async revertCustomAudio(){const s=this.studyCard;if(s){this.audioMessage="";try{if(!(await v.revertAudio(s.note_id)).reverted)throw new Error("The server did not confirm the change.");this.hasCustomAudio=!1,this.revertConfirmation=!1,this.audioMessage="Automatic pronunciation restored.",await this.refreshStudyFace(s.card_id)}catch(e){this.audioMessage=this.messageFor(e,"Automatic pronunciation could not be restored.")}}}selectedDeck(){return this.decks.find(s=>s.id===this.selectedDeckId)}manualDeck(){return this.decks.find(s=>s.id===this.manualDeckId)}resetManualSelection(){this.selectedCandidate=null,this.selectedSenseRef=null,this.selectedMeaningLanguages=["de","en"],this.userMeaningDe="",this.userMeaningEn=""}selectCandidate(s){var e,t;this.selectedCandidate=s,this.selectedSenseRef=s.status==="resolved"?((t=(e=s.senses)==null?void 0:e[0])==null?void 0:t.sense_semantic_ref)??null:null}toggleMeaningLanguage(s,e){this.selectedMeaningLanguages=e?[...new Set([...this.selectedMeaningLanguages,s])]:this.selectedMeaningLanguages.filter(t=>t!==s)}async lookup(s){s.preventDefault();const e=this.lookupQuery.trim();if(!e){this.errorMessage="Enter a German word before looking it up.",this.successMessage="";return}this.lookupStatus="loading",this.lookupCandidates=[],this.lookupAssetToken="",this.resetManualSelection(),this.errorMessage="",this.successMessage="";try{const t=await v.lookup(e),i=t.candidates.map(r=>{var n,h;return{...r,status:r.status??((n=r.senses)!=null&&n.length?"resolved":"needs_gloss"),senses:(h=r.senses)==null?void 0:h.map(c=>{var g,f;return{...c,gloss:c.gloss??((f=(g=c.meanings)==null?void 0:g[0])==null?void 0:f.text)??""}})}});this.lookupCandidates=i,this.lookupAssetToken=t.asset_token,this.lookupStatus="ready";const a=i.length===1?i[0]:void 0;a&&this.selectCandidate(a)}catch(t){this.lookupStatus="error",this.errorMessage=this.messageFor(t,"German vocabulary could not be looked up.")}}userMeanings(){const s={};return this.userMeaningDe.trim()&&(s.de=this.userMeaningDe.trim()),this.userMeaningEn.trim()&&(s.en=this.userMeaningEn.trim()),Object.keys(s).length?s:void 0}async saveManualNote(s){var i;s.preventDefault();const e=this.selectedCandidate,t=this.manualDeck();if(!e||!this.lookupAssetToken){this.errorMessage="Look up and select a German vocabulary candidate before saving.",this.successMessage="";return}if(!t){this.errorMessage="Select a deck before saving this vocabulary.",this.successMessage="";return}if(!this.selectedMeaningLanguages.length){this.errorMessage="Select German, English, or both meaning languages.",this.successMessage="";return}if(e.status==="resolved"&&!this.selectedSenseRef){this.errorMessage="Select a meaning for this resolved dictionary entry.",this.successMessage="";return}if(e.status==="derived_compound"&&!((i=e.component_refs)!=null&&i.length)){this.errorMessage="This derived compound has no supported component bindings to save.",this.successMessage="";return}this.isSavingNote=!0,this.errorMessage="",this.successMessage="";try{const a=await v.createNote({asset_token:this.lookupAssetToken,lemma_semantic_ref:e.lemma_semantic_ref,sense_semantic_ref:this.selectedSenseRef,status:e.status,component_refs:e.component_refs,meaning_languages:this.selectedMeaningLanguages,deck_name:t.name,user_meanings:this.userMeanings()}),r=await this.loadDecks();if(r===null){this.errorMessage=`“${e.lemma}” may have been saved, but the deck list could not be refreshed.`;return}const n=r.find(h=>h.id===a.deck_id);if(a.deck_id!==t.id||!n){this.errorMessage=`The server did not confirm “${e.lemma}” in the selected deck. It was not reported as saved.`;return}this.selectedDeckId=n.id,this.manualDeckId=n.id,this.successMessage=`Saved “${e.lemma}” to “${n.name}”.`,this.lookupQuery="",this.lookupCandidates=[],this.lookupAssetToken="",this.lookupStatus="idle",this.resetManualSelection()}catch(a){this.successMessage="",this.errorMessage=this.messageFor(a,"Vocabulary could not be saved.")}finally{this.isSavingNote=!1}}captureKey(s){return`${s.lemma_semantic_ref}:${s.status}`}updateCaptureSpan(s){const e=s.target;this.captureSpanStart=e.selectionStart??0,this.captureSpanEnd=e.selectionEnd??0}resetCapturePicker(){this.captureCandidates=[],this.captureAssetToken="",this.captureContext=null,this.captureSelections={},this.captureDictionaryChanged=!1}async highlightCapture(s){s==null||s.preventDefault();const e=this.captureSentence,t=this.captureLessonLabel.trim(),i={start:this.captureSpanStart,end:this.captureSpanEnd};if(!e.trim()){this.captureStatus="error",this.captureError="Enter the sentence you want this card to remember.";return}if(i.start===i.end){this.captureStatus="error",this.captureError="Select the German word or phrase in the sentence before finding candidates.";return}if(!t){this.captureStatus="error",this.captureError="Add a lesson label so this capture keeps its provenance.";return}this.captureStatus="loading",this.captureError="",this.resetCapturePicker();try{const a=await v.highlight({sentence_text:e,selected_span:i,lesson_label:t});this.captureCandidates=a.candidates,this.captureAssetToken=a.asset_token,this.captureContext=a.capture_context,this.captureStatus="ready";const r=a.candidates.length===1?a.candidates[0]:void 0;r&&this.toggleCaptureCandidate(r,!0)}catch(a){this.captureStatus="error",this.captureError=this.messageFor(a,"Candidates could not be found.")}}toggleCaptureCandidate(s,e){var a,r;const t=this.captureKey(s),i={...this.captureSelections};e?i[t]={candidate:s,senseRef:s.status==="resolved"?((r=(a=s.senses)==null?void 0:a[0])==null?void 0:r.sense_semantic_ref)??null:null}:delete i[t],this.captureSelections=i}setCaptureSense(s,e){const t=this.captureKey(s),i=this.captureSelections[t];i&&(this.captureSelections={...this.captureSelections,[t]:{...i,senseRef:e}})}toggleCaptureMeaningLanguage(s){const e=this.captureMeaningLanguages;if(e.includes(s)){if(e.length===1)return;this.captureMeaningLanguages=e.filter(t=>t!==s);return}this.captureMeaningLanguages=[...e,s]}captureUserMeanings(){const s={};return this.captureUserMeaningDe.trim()&&(s.de=this.captureUserMeaningDe.trim()),this.captureUserMeaningEn.trim()&&(s.en=this.captureUserMeaningEn.trim()),Object.keys(s).length?s:void 0}async saveCapture(s){s.preventDefault();const e=this.decks.find(a=>a.id===this.captureDeckId),t=Object.values(this.captureSelections);if(!t.length)return;if(!e){this.captureError="Choose a destination deck before creating cards.";return}if(!this.captureContext||!this.captureAssetToken){this.captureError="Find candidates again before creating cards.";return}if(t.some(({candidate:a,senseRef:r})=>a.status==="resolved"&&!r)){this.captureError="Choose a dictionary meaning for every selected candidate.";return}this.isCapturing=!0,this.captureError="",this.captureDictionaryChanged=!1,this.successMessage="";try{const a=await v.captureCards({asset_token:this.captureAssetToken,deck:{name:e.name,lesson_label:this.captureContext.lesson_label},capture_context:this.captureContext,selections:t.map(({candidate:g,senseRef:f})=>({lemma_semantic_ref:g.lemma_semantic_ref,sense_semantic_ref:f,status:g.status,component_refs:g.component_refs,overrides:{meaning_langs:this.captureMeaningLanguages,user_meanings:this.captureUserMeanings()}}))}),r=await this.loadDecks(),n=r==null?void 0:r.find(g=>g.id===a.deck_id);if(!n||n.id!==e.id){this.captureError="The server did not confirm the selected destination deck. Cards were not reported as created.";return}const h=a.notes.filter(g=>g.created).length,c=a.notes.length-h;this.selectedDeckId=n.id,this.manualDeckId=n.id,this.captureDeckId=n.id,this.successMessage=`Server confirmed ${h} ${h===1?"card":"cards"} created and ${c} ${c===1?"card":"cards"} reused in “${n.name}”.`,this.captureStatus="idle",this.captureSentence="",this.captureLessonLabel="",this.captureSpanStart=0,this.captureSpanEnd=0,this.captureUserMeaningDe="",this.captureUserMeaningEn="",this.resetCapturePicker()}catch(a){a instanceof N&&a.isConflict?(this.captureDictionaryChanged=!0,this.captureError=""):this.captureError=this.messageFor(a,"Cards could not be created.")}finally{this.isCapturing=!1}}async readImportFile(s){var t;const e=(t=s.target.files)==null?void 0:t[0];if(e){this.isReadingImportFile=!0,this.errorMessage="",this.successMessage="";try{this.importText=await e.text(),this.importFileName=e.name}catch(i){this.importFileName="",this.errorMessage=this.messageFor(i,"The selected file could not be read.")}finally{this.isReadingImportFile=!1}}}async importCsv(s){s.preventDefault();const e=this.importDeckName.trim(),t=this.importText.trim();if(!e){this.errorMessage="Enter the deck name for this CSV import.",this.successMessage="";return}if(!t){this.errorMessage="Paste vocabulary lines or choose a CSV/text file before importing.",this.successMessage="";return}this.isImporting=!0,this.errorMessage="",this.successMessage="";try{const i=await v.importCsv({csv_text:t,deck_name:e}),a=await this.loadDecks();if(a===null){this.errorMessage="The import may have completed, but the deck list could not be refreshed.";return}const r=a.find(n=>n.id===i.deck_id);if(!r){this.errorMessage="The server did not return the import deck after completion. The import was not reported as successful.";return}this.selectedDeckId=r.id,this.manualDeckId=r.id,this.importDeckName=r.name,this.successMessage=`Imported ${i.total_words} ${i.total_words===1?"word":"words"} into “${r.name}”: ${i.notes_created} created, ${i.notes_reused} reused.`,this.importText="",this.importFileName=""}catch(i){this.successMessage="",this.errorMessage=this.messageFor(i,"CSV import could not be completed.")}finally{this.isImporting=!1}}async exportTsv(s){this.exportingFormat="tsv",this.errorMessage="",this.successMessage="";try{const e=await v.exportAnki(s.id),t=URL.createObjectURL(new Blob([e],{type:"text/tab-separated-values;charset=utf-8"})),i=document.createElement("a");i.href=t,i.download=`${s.name.replace(/[^a-z0-9._-]+/gi,"-")||"flashcards"}.tsv`,i.click(),URL.revokeObjectURL(t),this.successMessage=`Prepared a TSV export for “${s.name}”.`}catch(e){this.errorMessage=this.messageFor(e,"TSV export could not be prepared.")}finally{this.exportingFormat=null}}async exportApkg(s){this.exportingFormat="apkg",this.errorMessage="",this.successMessage="";try{const e=await v.exportApkg(s.id),t=URL.createObjectURL(e),i=document.createElement("a");i.href=t,i.download=`${s.name.replace(/[^a-z0-9._-]+/gi,"-")||"flashcards"}.apkg`,i.click(),URL.revokeObjectURL(t),this.successMessage=`Prepared an APKG export for “${s.name}”.`}catch(e){this.errorMessage=this.messageFor(e,"APKG export could not be prepared.")}finally{this.exportingFormat=null}}renderNotices(){return o`
      ${this.errorMessage?o`<div class="notice error" role="alert">${this.errorMessage}</div>`:p}
      ${this.successMessage?o`<div class="notice success" role="status">${this.successMessage}</div>`:p}
    `}renderDeckList(){return this.deckStatus==="loading"?o`<p class="loading" role="status">Loading decks…</p>`:this.deckStatus==="error"?o`<div class="empty"><p>We could not reach your deck list.</p><button @click=${this.loadDecks}>Try again</button></div>`:this.decks.length===0?o`<div class="empty"><p>No decks yet. Create one to begin organizing German vocabulary.</p></div>`:o`
      <ul class="deck-list" aria-label="Your decks">
        ${this.decks.map(s=>o`
          <li class="deck">
            <button class="deck-open" @click=${()=>this.openDeck(s)} aria-label=${`Open ${s.name}`}>
              <span class="deck-name">${s.name}</span>
              <span class="deck-stats">${s.card_count} ${s.card_count===1?"card":"cards"} · ${s.due_count} due · ${s.mastery_percent}% mastered</span>
            </button>
            ${this.pendingDeleteDeckId===s.id?o`
              <div class="actions confirm" aria-label=${`Confirm deletion of ${s.name}`}>
                <button class="danger" ?disabled=${this.isDeleting} @click=${()=>void this.deleteDeck(s)}>${this.isDeleting?"Deleting…":"Confirm delete"}</button>
                <button ?disabled=${this.isDeleting} @click=${()=>{this.pendingDeleteDeckId=null}}>Cancel</button>
              </div>
            `:o`
              <button class="danger" @click=${()=>{this.pendingDeleteDeckId=s.id,this.successMessage=""}}>Delete</button>
            `}
          </li>
        `)}
      </ul>
    `}renderSenseChoices(s){return o`
      <fieldset class="selection">
        <legend>Dictionary meaning</legend>
        <ul class="choice-list">
          ${s.map(e=>o`
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
    `}renderManualCreation(){var t;const s=this.selectedCandidate,e=this.manualDeck();return o`
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
        ${this.lookupStatus==="loading"?o`<p class="result" role="status">Looking up the active dictionary…</p>`:p}
        ${this.lookupStatus==="ready"&&!this.lookupCandidates.length?o`<p class="result">No dictionary candidate was returned. Try a different German form.</p>`:p}
        ${this.lookupCandidates.length?o`
          <fieldset class="selection">
            <legend>Select vocabulary</legend>
            <ul class="candidate-list">
              ${this.lookupCandidates.map(i=>o`
                <li>
                  <button
                    class="candidate ${s===i?"selected":""}"
                    type="button"
                    @click=${()=>this.selectCandidate(i)}
                    aria-pressed=${s===i?"true":"false"}
                  >
                    ${i.lemma} · ${i.pos}
                    <small>${i.status==="resolved"?"Dictionary entry":i.status.replace("_"," ")}</small>
                  </button>
                </li>
              `)}
            </ul>
          </fieldset>
        `:p}
        ${s?o`
          <form @submit=${this.saveManualNote}>
            ${s.status==="resolved"?(t=s.senses)!=null&&t.length?this.renderSenseChoices(s.senses):o`<p class="result">This result has no selectable sense and cannot be saved as a resolved note.</p>`:p}
            ${s.status==="derived_compound"?o`<p class="result">The server will retain this compound’s supported component bindings.</p>`:p}
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
        `:p}
      </section>
    `}renderCaptureCreation(s){const e=Object.keys(this.captureSelections).length,t=this.decks.find(a=>a.id===this.captureDeckId),i=this.captureSentence.slice(this.captureSpanStart,this.captureSpanEnd);return o`
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
        ${this.captureStatus==="loading"?o`<p class="result" role="status">Checking the active dictionary…</p>`:p}
        ${this.captureStatus==="error"?o`<div class="capture-state error" role="alert"><p>${this.captureError}</p><button @click=${()=>void this.highlightCapture()}>Try again</button></div>`:p}
        ${this.captureStatus==="ready"&&this.captureCandidates.length===0?o`<div class="capture-state"><p>No dictionary candidates were found for “${i}”. Adjust the selected text and try again.</p></div>`:p}
        ${this.captureCandidates.length?o`
          <form class="capture-picker" @submit=${this.saveCapture}>
            <fieldset class="selection">
              <legend>Choose vocabulary <span class="muted">(select one or more)</span></legend>
              <p class="result">Each checked German candidate becomes its own card. You can select multiple candidates.</p>
              <ul class="candidate-list">
                ${this.captureCandidates.map(a=>{var h;const r=this.captureKey(a),n=this.captureSelections[r];return o`
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
                      ${n&&a.status==="resolved"?(h=a.senses)!=null&&h.length?o`
                        <fieldset class="sense-choices">
                          <legend>Dictionary meaning for ${a.lemma}</legend>
                          ${a.senses.map(c=>o`
                            <label class="choice">
                              <input type="radio" name=${`capture-sense-${r}`} .value=${c.sense_semantic_ref} .checked=${n.senseRef===c.sense_semantic_ref} @change=${()=>this.setCaptureSense(a,c.sense_semantic_ref)} ?disabled=${this.isCapturing} />
                              ${c.gloss||`Meaning ${c.ord}`}
                            </label>
                          `)}
                        </fieldset>
                      `:o`<p class="result">This entry has no selectable dictionary meaning.</p>`:p}
                      ${n&&a.status==="derived_compound"?o`<p class="result">The server will preserve the compound’s dictionary component bindings.</p>`:p}
                    </li>
                  `})}
              </ul>
            </fieldset>
            ${this.captureDictionaryChanged?o`
              <div class="capture-state warning" role="alert">
                <p>The dictionary changed while you were choosing cards. Your selections have not been saved.</p>
                <button type="button" @click=${()=>void this.highlightCapture()}>Find fresh candidates</button>
              </div>
            `:p}
            ${this.captureError?o`<div class="capture-state error" role="alert"><p>${this.captureError}</p></div>`:p}
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
            ${this.captureMeaningLanguages.includes("de")?o`<label>Your German meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningDe} @input=${a=>{this.captureUserMeaningDe=a.target.value}} ?disabled=${this.isCapturing} autocomplete="off" /></label>`:p}
            ${this.captureMeaningLanguages.includes("en")?o`<label>Your English meaning <span class="muted">(optional)</span><input .value=${this.captureUserMeaningEn} @input=${a=>{this.captureUserMeaningEn=a.target.value}} ?disabled=${this.isCapturing} autocomplete="off" /></label>`:p}
            <label>Destination deck
              <select .value=${String(t?t.id:s.id)} @change=${a=>{const r=a.target.value;this.captureDeckId=r?Number(r):null}} ?disabled=${this.isCapturing}>
                <option value="">Select a deck</option>
                ${this.decks.map(a=>o`<option value=${a.id}>${a.name}</option>`)}
              </select>
            </label>
            <div class="actions create-actions">
              <button class="primary" type="submit" ?disabled=${e===0||this.isCapturing||this.captureDictionaryChanged}>${this.isCapturing?"Creating cards…":`Create ${e||""} card${e===1?"":"s"}`}</button>
              ${e===0?o`<p class="disabled-explanation">Select at least one candidate to create cards.</p>`:p}
            </div>
          </form>
        `:p}
      </section>
    `}renderImportExport(s){return o`
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
          ${this.isReadingImportFile?o`<p class="result" role="status">Reading file…</p>`:p}
          ${this.importFileName?o`<p class="result">Using text from ${this.importFileName}.</p>`:p}
          <div class="actions"><button class="primary" type="submit" ?disabled=${this.isImporting||this.isReadingImportFile}>${this.isImporting?"Importing…":"Import CSV"}</button></div>
        </form>
        <div class="workflow-grid">
          <div>
            <h3>APKG export</h3>
            <p class="muted">Download the selected deck as a ready-to-import Anki package.</p>
            <button class="primary" @click=${()=>void this.exportApkg(s)} ?disabled=${this.exportingFormat!==null}>${this.exportingFormat==="apkg"?"Preparing APKG…":`Export “${s.name}” APKG`}</button>
          </div>
          <div>
            <h3>TSV export</h3>
            <p class="muted">Secondary export for the available Anki TSV format.</p>
            <button @click=${()=>void this.exportTsv(s)} ?disabled=${this.exportingFormat!==null}>${this.exportingFormat==="tsv"?"Preparing TSV…":`Export “${s.name}” TSV`}</button>
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
        ${this.audioMessage?o`<p class="inline-status ${this.audioStatus==="unavailable"?"error":""}" role=${this.audioStatus==="unavailable"?"alert":"status"}>${this.audioMessage}</p>`:p}
      </div>
    `}renderPronunciationManagement(){const s=this.recordingStatus==="save-error";return o`
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
            `:p}
            ${s?o`
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
                `:p}
              </div>
              ${this.recordingError?o`<p class="inline-status error" role="alert">${this.recordingError}</p>`:p}
            `}
          </div>
        `:p}
      </section>
    `}renderMeaningEditor(s){return o`
      <section class="edit-meanings" aria-labelledby="meaning-edit-title">
        <h3 id="meaning-edit-title">Your meanings</h3>
        <p class="muted">Save your wording for either language, or remove an existing personal meaning to return to the card’s available meaning.</p>
        ${["de","en"].map(e=>{const t=this.meaningFor(s,e),i=!!(t!=null&&t.is_user_authored);return o`
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
              ${i?o`<button class="danger" type="button" @click=${()=>void this.deleteGloss(e)} ?disabled=${this.glossSavingLanguage===e}>Remove</button>`:p}
            </div>
          `})}
        ${this.glossState?o`<p class="inline-status" role="status">${this.glossState}</p>`:p}
        ${this.glossError?o`<p class="inline-status error" role="alert">${this.glossError}</p>`:p}
      </section>
    `}renderStudyCard(s){const e=this.meaningFor(s,"de"),t=this.meaningFor(s,"en"),i=s.back.examples[0],a=s.back.examples.slice(1),r=s.back.meanings.flatMap(n=>n.lines.slice(1).map(h=>`${n.heading}: ${h}`));return o`
      <div class="card-stage">
        <div class="card-side">
          <span class="front-label">German vocabulary</span>
          <h2 class="study-lemma">${s.front.display_headword}</h2>
          <p class="study-meta">${s.front.pos}${s.front.ipa?` · ${s.front.ipa}`:""}</p>
          ${this.isRevealed?o`
            <div class="card-side" data-study-answer tabindex="-1">
              <hr class="answer-rule" />
              <span class="front-label">Answer</span>
              <p class="meaning"><span class="meaning-label">German</span><br />${(e==null?void 0:e.lines[0])??"No German learner meaning is available."}</p>
              ${t?o`<p class="meaning"><span class="meaning-label">English</span><br />${t.lines[0]??""}</p>`:p}
              ${i?o`<p class="example">${i.de}${i.en?o`<span class="example-translation">${i.en}</span>`:p}</p>`:p}
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
                  <div class="detail-block"><span class="meaning-label">Grammar</span><p>${s.back.grammar.lines.join(" · ")||s.back.pos}</p></div>
                  ${r.length?o`<div class="detail-block"><span class="meaning-label">Extended notes</span><ul>${r.map(n=>o`<li>${n}</li>`)}</ul></div>`:p}
                  ${a.length?o`<div class="detail-block"><span class="meaning-label">Additional examples</span>${a.map(n=>o`<p class="example">${n.de}${n.en?o`<span class="example-translation">${n.en}</span>`:p}</p>`)}</div>`:p}
                  ${this.renderPronunciationManagement()}
                  ${this.renderMeaningEditor(s)}
                </div>
              `:p}
              <div>
                <p class="front-label">How well did you know it?</p>
                <div class="confidence-grid">
                  ${Ye.map(([n,h])=>o`
                    <button class="confidence" type="button" ?disabled=${this.isReviewing||!!this.recordingBlob} @click=${()=>void this.submitConfidence(Number(n))}>
                      <span class="confidence-number">${n}</span><span class="confidence-text">${h}</span>
                    </button>
                  `)}
                </div>
              </div>
              ${this.isReviewing?o`<p class="inline-status" role="status">Saving your confidence…</p>`:p}
              ${this.recordingBlob?o`<p class="inline-status">Save or discard the local recording before choosing a confidence.</p>`:p}
            </div>
          `:o`
            <button class="primary reveal-action" type="button" @click=${this.revealCard}>Reveal answer <span class="caption">Space</span></button>
          `}
        </div>
      </div>
    `}renderStudy(){const s=this.decks.find(e=>e.id===this.studyDeckId);return o`
      <main class="study" aria-labelledby="study-title">
        <div class="study-heading">
          <div><p class="caption">Study</p><h2 id="study-title">${s?s.name:"All due cards"}</h2></div>
          <button type="button" @click=${()=>void this.loadStudyCard()} ?disabled=${this.studyStatus==="loading"}>${this.studyStatus==="loading"?"Loading…":"Refresh"}</button>
        </div>
        ${this.studyStatus==="ready"&&this.studyError?o`<p class="inline-status error" role="alert">${this.studyError}</p>`:p}
        ${this.studyStatus==="loading"?o`<div class="card-stage study-state" role="status">Loading the next due card…</div>`:p}
        ${this.studyStatus==="error"?o`<div class="card-stage study-state"><div><h2>Could not load a card</h2><p class="inline-status error" role="alert">${this.studyError}</p><button class="primary" type="button" @click=${()=>void this.loadStudyCard()}>Try again</button></div></div>`:p}
        ${this.studyStatus==="empty"?o`<div class="card-stage study-state" data-study-empty tabindex="-1"><div><h2>Nothing due right now</h2><p class="muted">Your next due card will appear here when the server has one ready.</p><button type="button" @click=${()=>void this.loadStudyCard()}>Check again</button></div></div>`:p}
        ${this.studyStatus==="ready"&&this.studyCard?this.renderStudyCard(this.studyCard):p}
      </main>
    `}renderDeckDetail(s){return o`
      <section class="panel" aria-labelledby="deck-title">
        <div class="deck-heading">
          <div>
            <h2 id="deck-title">${s.name}</h2>
            <p class="muted">${s.card_count} ${s.card_count===1?"card":"cards"} · ${s.due_count} due · ${s.mastery_percent}% mastered</p>
          </div>
          <div class="actions"><button class="primary" @click=${()=>void this.openStudy(s.id)}>Study this deck</button><button @click=${()=>{this.selectedDeckId=null,this.view="decks"}}>All decks</button></div>
        </div>
        <p>Card data and review scheduling remain on the server.</p>
        <div class="workflow-grid">
          ${this.renderCaptureCreation(s)}
          ${this.renderManualCreation()}
          ${this.renderImportExport(s)}
        </div>
      </section>
    `}render(){const s=this.selectedDeck(),e=this.deckStatus!=="ready"||!s;return o`
      <div class="shell">
        <header>
          <div>
            <h1>Wortlaut</h1>
            <div class="subtitle">German vocabulary</div>
          </div>
          <nav class="primary-nav" aria-label="Main navigation">
            <button type="button" aria-current=${this.view==="study"?"false":"page"} @click=${()=>{this.view="decks",this.selectedDeckId=null}}>Decks</button>
            <button type="button" aria-current=${this.view==="study"?"page":"false"} @click=${()=>void this.openStudy()}>Study due</button>
            <button type="button" @click=${this.loadDecks} ?disabled=${this.deckStatus==="loading"}>${this.deckStatus==="loading"?"Refreshing…":"Refresh decks"}</button>
          </nav>
        </header>
        ${this.renderNotices()}
        ${this.view==="study"?this.renderStudy():e?o`
          <main class="panel">
            <div class="toolbar"><h2>Your decks</h2><span class="muted" aria-live="polite">${this.deckStatus==="ready"?"Server-synced":""}</span></div>
            <form class="form-row" @submit=${this.createDeck}>
              <label>New deck name
                <input .value=${this.newDeckName} @input=${t=>{this.newDeckName=t.target.value}} ?disabled=${this.isCreating} maxlength="200" autocomplete="off" />
              </label>
              <button class="primary" type="submit" ?disabled=${this.isCreating}>${this.isCreating?"Creating…":"Create deck"}</button>
            </form>
            ${this.renderDeckList()}
          </main>
        `:this.renderDeckDetail(s)}
      </div>
      <nav class="bottom-nav" aria-label="Main navigation">
        <button type="button" aria-current=${this.view==="study"?"false":"page"} @click=${()=>{this.view="decks",this.selectedDeckId=null}}>Decks</button>
        <button type="button" aria-current=${this.view==="study"?"page":"false"} @click=${()=>void this.openStudy()}>Study due</button>
      </nav>
    `}};l.styles=ye`
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
  `;d([u()],l.prototype,"decks",2);d([u()],l.prototype,"deckStatus",2);d([u()],l.prototype,"errorMessage",2);d([u()],l.prototype,"successMessage",2);d([u()],l.prototype,"newDeckName",2);d([u()],l.prototype,"selectedDeckId",2);d([u()],l.prototype,"pendingDeleteDeckId",2);d([u()],l.prototype,"isCreating",2);d([u()],l.prototype,"isDeleting",2);d([u()],l.prototype,"lookupQuery",2);d([u()],l.prototype,"lookupStatus",2);d([u()],l.prototype,"lookupCandidates",2);d([u()],l.prototype,"lookupAssetToken",2);d([u()],l.prototype,"selectedCandidate",2);d([u()],l.prototype,"selectedSenseRef",2);d([u()],l.prototype,"selectedMeaningLanguages",2);d([u()],l.prototype,"userMeaningDe",2);d([u()],l.prototype,"userMeaningEn",2);d([u()],l.prototype,"manualDeckId",2);d([u()],l.prototype,"isSavingNote",2);d([u()],l.prototype,"importDeckName",2);d([u()],l.prototype,"importText",2);d([u()],l.prototype,"importFileName",2);d([u()],l.prototype,"isReadingImportFile",2);d([u()],l.prototype,"isImporting",2);d([u()],l.prototype,"exportingFormat",2);d([u()],l.prototype,"captureSentence",2);d([u()],l.prototype,"captureLessonLabel",2);d([u()],l.prototype,"captureSpanStart",2);d([u()],l.prototype,"captureSpanEnd",2);d([u()],l.prototype,"captureStatus",2);d([u()],l.prototype,"captureCandidates",2);d([u()],l.prototype,"captureAssetToken",2);d([u()],l.prototype,"captureContext",2);d([u()],l.prototype,"captureSelections",2);d([u()],l.prototype,"captureMeaningLanguages",2);d([u()],l.prototype,"captureUserMeaningDe",2);d([u()],l.prototype,"captureUserMeaningEn",2);d([u()],l.prototype,"captureDeckId",2);d([u()],l.prototype,"captureError",2);d([u()],l.prototype,"captureDictionaryChanged",2);d([u()],l.prototype,"isCapturing",2);d([u()],l.prototype,"view",2);d([u()],l.prototype,"studyDeckId",2);d([u()],l.prototype,"studyStatus",2);d([u()],l.prototype,"studyCard",2);d([u()],l.prototype,"isRevealed",2);d([u()],l.prototype,"isReviewing",2);d([u()],l.prototype,"studyError",2);d([u()],l.prototype,"extraInfoOpen",2);d([u()],l.prototype,"alwaysShowExtraInfo",2);d([u()],l.prototype,"glossDrafts",2);d([u()],l.prototype,"glossState",2);d([u()],l.prototype,"glossError",2);d([u()],l.prototype,"glossSavingLanguage",2);d([u()],l.prototype,"audioStatus",2);d([u()],l.prototype,"audioMessage",2);d([u()],l.prototype,"recordingStatus",2);d([u()],l.prototype,"recordingBlob",2);d([u()],l.prototype,"recordingNoteId",2);d([u()],l.prototype,"recordingPreviewUrl",2);d([u()],l.prototype,"recordingError",2);d([u()],l.prototype,"showRecordingControls",2);d([u()],l.prototype,"revertConfirmation",2);d([u()],l.prototype,"hasCustomAudio",2);l=d([Oe("flashcard-app")],l);
