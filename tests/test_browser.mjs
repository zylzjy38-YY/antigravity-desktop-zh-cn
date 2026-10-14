// Run with TEST_PLAYWRIGHT_PATH and TEST_PYTHON set, or installed playwright/Python.
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn} from 'node:child_process';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.TEST_PLAYWRIGHT_PATH || 'playwright');
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const runtime=fs.readFileSync(path.join(root,'localization/runtime.js'),'utf8');
const dictionary=JSON.parse(fs.readFileSync(path.join(root,'localization/zh-CN.json'),'utf8'));
const source=`(${runtime})(${JSON.stringify({dictionary})});`;
const html=`<!doctype html><html><body>
<button id="save" title="Save">Save</button><div id="settings">Settings</div>
<input id="input" value="Save" placeholder="Save"><textarea id="textarea" placeholder="Save">Save</textarea>
<div contenteditable="true" id="editable">Save</div><pre id="code">Save</pre>
<article id="chat"><p>Save</p><button id="copy" aria-label="Copy">Save</button></article>
<div class="markdown" id="markdown">Save</div><div class="xterm" id="terminal">Save</div>
<div data-testid="project-header" id="project">Settings</div>
<a href="/c/test" id="conversation">Settings</a>
<div data-testid="tool-call-output" id="tool" title="Save">Save</div>
<div data-testid="artifact-content" id="artifact">Save</div>
<button id="unknown">hasOwnProperty</button><span id="prototype">toString</span>
</body></html>`;
const server=http.createServer((request,response)=>{response.writeHead(200,{'Content-Type':'text/html;charset=utf-8'});response.end(html);});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const reservation=net.createServer();await new Promise(resolve=>reservation.listen(0,'127.0.0.1',resolve));
const debugPort=reservation.address().port;await new Promise(resolve=>reservation.close(resolve));
const browser=await chromium.launch({channel:'msedge',headless:true,args:[`--remote-debugging-port=${debugPort}`,'--remote-debugging-address=127.0.0.1']});
let assertions=0;
let child;
function eq(actual,expected){assert.equal(actual,expected);assertions++;}
try{
  const page=await browser.newPage();
  await page.goto(`http://127.0.0.1:${server.address().port}/`);
  // Exercise the actual Python WebSocket client and injection registration.
  const python=`import json,sys\nfrom pathlib import Path\nsys.path.insert(0,${JSON.stringify(root)})\nfrom protocol import list_targets,local_page,Cdp\nfrom worker import ensure_translation\np=Path(${JSON.stringify(root)})\nd=json.loads((p/'localization/zh-CN.json').read_text(encoding='utf-8'))\ns='('+ (p/'localization/runtime.js').read_text(encoding='utf-8') +')('+json.dumps({'dictionary':d},ensure_ascii=False)+');'\nt=next(x for x in list_targets(${debugPort}) if local_page(x))\nc=Cdp(t['webSocketDebuggerUrl'],${debugPort})\nassert ensure_translation(c,s)\nprint('Python CDP injection verified',flush=True)\nsys.stdin.readline()\nc.close()`;
  child=spawn(process.env.TEST_PYTHON || 'python',['-X','utf8','-c',python]);
  await new Promise((resolve,reject)=>{let errors='';child.stderr.on('data',value=>errors+=value);child.stdout.once('data',value=>{console.log(value.toString().trim());resolve();});child.once('exit',code=>reject(Error(`Python CDP exited ${code}: ${errors}`)));child.once('error',reject);});
  eq(await page.locator('#save').textContent(),'保存');eq(await page.locator('#save').getAttribute('title'),'保存');
  eq(await page.locator('#input').inputValue(),'Save');eq(await page.locator('#input').getAttribute('placeholder'),'保存');
  eq(await page.locator('#textarea').inputValue(),'Save');
  for(const id of ['editable','code','chat p','markdown','terminal','tool','artifact']) eq(await page.locator('#'+id).textContent(),'Save');
  eq(await page.locator('#project').textContent(),'Settings');eq(await page.locator('#conversation').textContent(),'Settings');
  eq(await page.locator('#tool').getAttribute('title'),'Save');eq(await page.locator('#copy').getAttribute('aria-label'),'复制');
  eq(await page.locator('#unknown').textContent(),'hasOwnProperty');eq(await page.locator('#prototype').textContent(),'toString');
  await page.evaluate(()=>{const button=document.createElement('button');button.id='dynamic';button.textContent='Cancel';document.body.appendChild(button);});
  await page.waitForFunction(()=>document.querySelector('#dynamic')?.textContent==='取消'); assertions++;
  await page.locator('#save').evaluate(e=>e.textContent='Cancel');
  await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='取消'); assertions++;
  await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='保存');assertions++;
  await page.evaluate(()=>{const body=document.createElement('body');body.innerHTML='<button id="replacement">Save</button><article>Save</article>';document.body.replaceWith(body);});
  await page.waitForFunction(()=>document.querySelector('#replacement')?.textContent==='保存');eq(await page.locator('article').textContent(),'Save');assertions++;
  await page.evaluate(source);eq(await page.evaluate(()=>Boolean(globalThis.__antigravityChineseObserver)),true);
  // The same source cannot run on a remote page; no navigation to the internet is needed.
  const remote=await browser.newPage();await remote.route('https://example.test/',route=>route.fulfill({contentType:'text/html',body:'<button>Save</button>'}));
  await remote.goto('https://example.test/');await remote.evaluate(source);eq(await remote.locator('button').textContent(),'Save');
  console.log(`Browser behavior assertions passed: ${assertions}`);
}finally{if(child){child.stdin.end('\n');await new Promise(resolve=>child.once('exit',resolve));}await browser.close();await new Promise(resolve=>server.close(resolve));}
