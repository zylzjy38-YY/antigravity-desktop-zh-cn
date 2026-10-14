// An isolated fake Antigravity process proxies Edge's CDP. No installed app is changed.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import http from 'node:http';
import net from 'node:net';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {spawn,spawnSync} from 'node:child_process';
import assert from 'node:assert/strict';
const require=createRequire(import.meta.url);
const {chromium}=require(process.env.TEST_PLAYWRIGHT_PATH||'playwright');
const python=process.env.TEST_PYTHON||'python';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const temp=fs.mkdtempSync(path.join(os.tmpdir(),'antigravity-packed-test-'));
const exe=path.join(root,'dist','Antigravity中文.exe');
const fixture=path.join(temp,'Antigravity.exe');
const fixtureSource=String.raw`using System;using System.IO;using System.Net;using System.Net.Sockets;using System.Text;using System.Threading.Tasks;using System.Reflection;
[assembly:AssemblyFileVersion("2.23.0.0")]
class Fixture {
 static int upstream;
 static async Task Handle(TcpClient client,int local) {
  try {using(client) {var input=client.GetStream();var header=new MemoryStream();int state=0;
   while(state<4) {int b=input.ReadByte();if(b<0)return;header.WriteByte((byte)b);state=(state==0&&b==13)?1:(state==1&&b==10)?2:(state==2&&b==13)?3:(state==3&&b==10)?4:0;if(header.Length>65536)return;}
   string text=Encoding.ASCII.GetString(header.ToArray());
   if(text.StartsWith("GET /json/list ")) {using(var web=new WebClient()) {web.Proxy=null;string data=web.DownloadString("http://127.0.0.1:"+upstream+"/json/list").Replace(":"+upstream+"/",":"+local+"/");byte[] body=Encoding.UTF8.GetBytes(data);byte[] head=Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "+body.Length+"\r\nConnection: close\r\n\r\n");await input.WriteAsync(head,0,head.Length);await input.WriteAsync(body,0,body.Length);}return;}
   using(var target=new TcpClient("127.0.0.1",upstream)) {var output=target.GetStream();byte[] bytes=header.ToArray();await output.WriteAsync(bytes,0,bytes.Length);await Task.WhenAny(input.CopyToAsync(output),output.CopyToAsync(input));}
  }}catch{}
 }
 static void Main(string[] args) {upstream=int.Parse(args[0]);var listener=new TcpListener(IPAddress.Loopback,0);listener.Start();int port=((IPEndPoint)listener.LocalEndpoint).Port;Console.WriteLine(port);Console.Out.Flush();while(true){var client=listener.AcceptTcpClient();Task.Run(()=>Handle(client,port));}}
}`;
fs.writeFileSync(path.join(temp,'fixture.cs'),fixtureSource);
const compiler=path.join(process.env.WINDIR,'Microsoft.NET','Framework64','v4.0.30319','csc.exe');
const compiled=spawnSync(compiler,['/nologo','/target:exe','/out:'+fixture,path.join(temp,'fixture.cs')],{encoding:'utf8'});
assert.equal(compiled.status,0,compiled.stdout+compiled.stderr);
const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html');res.end('<button id="save">Save</button><article>Save</article>');});
await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
const reservation=net.createServer();await new Promise(resolve=>reservation.listen(0,'127.0.0.1',resolve));const port=reservation.address().port;await new Promise(resolve=>reservation.close(resolve));
const browser=await chromium.launch({channel:'msedge',headless:true,args:[`--remote-debugging-port=${port}`,'--remote-debugging-address=127.0.0.1']});
let proxy;
const localAppData=path.join(temp,'appdata'),installed=path.join(localAppData,'AntigravityDesktopZhCn');
fs.mkdirSync(localAppData);fs.mkdirSync(path.join(temp,'desktop'));
try{
  const page=await browser.newPage();await page.goto(`http://127.0.0.1:${server.address().port}/`);
  proxy=spawn(fixture,[String(port)]);
  await new Promise((resolve,reject)=>{proxy.stdout.once('data',resolve);proxy.once('error',reject);proxy.once('exit',code=>reject(Error('fixture exited '+code)));});
  // Install the built executable with the same core code, but into isolated paths.
  const setup=`import sys\nfrom pathlib import Path\nsys.path.insert(0,${JSON.stringify(root)})\nimport tool\nsys.frozen=True\nsys.executable=${JSON.stringify(exe)}\ntool.install(Path(${JSON.stringify(fixture)}),Path(${JSON.stringify(installed)}),Path(${JSON.stringify(path.join(temp,'desktop'))}))`;
  const result=spawnSync(python,['-X','utf8','-c',setup],{encoding:'utf8'});assert.equal(result.status,0,result.stdout+result.stderr);
  const launcher=spawn(path.join(installed,'Antigravity中文.exe'),['--launch'],{env:{...process.env,LOCALAPPDATA:localAppData}});
  const exit=await new Promise((resolve,reject)=>{launcher.once('exit',resolve);launcher.once('error',reject);});assert.equal(exit,0);
  await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='保存');
  assert.equal(await page.locator('article').textContent(),'Save');
  const first=JSON.parse(fs.readFileSync(path.join(installed,'status.json'),'utf8'));assert.ok(first.healthyPages>0);
  await new Promise(resolve=>setTimeout(resolve,6500));
  const later=JSON.parse(fs.readFileSync(path.join(installed,'status.json'),'utf8'));assert.ok(later.at>first.at && later.healthyPages>0);
  await page.reload();await page.waitForFunction(()=>document.querySelector('#save')?.textContent==='保存');
  console.log('Packaged launcher exit, independent worker survival and reload translation: passed');
  proxy.kill();await new Promise(resolve=>proxy.once('exit',resolve));proxy=null;
  await new Promise(resolve=>setTimeout(resolve,35000));
  const cleanup=`import sys\nfrom pathlib import Path\nsys.path.insert(0,${JSON.stringify(root)})\nimport tool\ntool.uninstall(Path(${JSON.stringify(installed)}))`;
  const removed=spawnSync(python,['-X','utf8','-c',cleanup],{encoding:'utf8'});assert.equal(removed.status,0,removed.stdout+removed.stderr);assert.ok(!fs.existsSync(installed));
  console.log('Packaged worker auto-exit and isolated uninstall: passed');
}finally{
  if(proxy)proxy.kill();await browser.close();await new Promise(resolve=>server.close(resolve));
  // Keep failed fixtures for diagnosis; successful runs contain no active worker.
  if(!fs.existsSync(installed))fs.rmSync(temp,{recursive:true});else console.log('Failed fixture retained:',temp);
}
