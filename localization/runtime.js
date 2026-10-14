(function installAntigravityChinese(options) {
  if (window !== window.top) return;
  if (!['https:', 'http:'].includes(location.protocol) ||
      !['127.0.0.1', 'localhost', '[::1]'].includes(location.hostname)) return;
  if (globalThis.__antigravityChineseVersion === 1 && globalThis.__antigravityChineseObserver) return;
  function start() {
    if (!document.body) return;
    globalThis.__antigravityChineseObserver?.disconnect();
    clearInterval(globalThis.__antigravityChineseTimer);
    const dictionary = options.dictionary || {};
    const lookup = text => Object.hasOwn(dictionary, text) && typeof dictionary[text] === 'string' ? dictionary[text] : undefined;
    const content = 'script,style,pre,code,kbd,samp,textarea,input,[contenteditable]:not([contenteditable="false"]),.monaco-editor,.xterm,.markdown,.prose,[data-message-id],[data-testid="conversation-message"],.chat-message,.message-content,.token,.shiki,.font-mono,[data-testid="user-input-step"] [data-quotable],[data-testid="user-message-document-chip"],.context-scope-mention,[data-quotable-inline]';
    const names = '[data-testid="project-header"],a[href*="/c/"],[data-agent-zh-preserve],[data-testid="settings-nav-item-Account"],[data-testid="project-selector-item"][data-project-name] span[title],[data-testid="project-selector-trigger"] span';
    const uiInArticle = '[role="menu"],[role="tooltip"],[data-testid="tool-group-collapsible"],[data-testid="thinking-collapsible-trigger"]';
    const articleLabels = new Set(['Copy','Copy code','At mention code block','Undo to this point','Good response','Bad response','Scroll to Bottom','Copy thinking','Collapse','Expand']);
    const userNames = new Set();
    const protectedRoots = new WeakSet();
    const normalized = value => value.replace(/\s+/g, ' ').trim();
    function rememberNames() {
      for (const e of document.querySelectorAll(names)) {
        const name = normalized(e.textContent || e.getAttribute('aria-label') || '');
        if (name) userNames.add(name);
      }
      // Project entries in Settings are dynamic, even when named General or Settings.
      for (const heading of document.querySelectorAll('.settings-modal-container h2')) {
        if (['Projects', '项目', '项目管理'].includes(heading.textContent.trim())) {
          const list = heading.parentElement.nextElementSibling;
          if (list) {protectedRoots.add(list); for (const e of list.querySelectorAll('*')) protectedRoots.add(e);}
        }
        if (userNames.has(heading.textContent.trim()) && heading.parentElement.querySelector('button')) protectedRoots.add(heading);
      }
    }
    function protectedElement(e) {
      if (protectedRoots.has(e) || e.closest(content + ',' + names)) return true;
      // Rendered message prose, tool commands and file paths are never rewritten.
      const article = e.closest('article,[role="article"]');
      if (article && !e.closest(uiInArticle)) return true;
      if (e.closest('[data-testid="tool-call-output"],[data-testid="tool-call-command"],[data-testid="artifact-content"],[data-testid="file-content"]')) return true;
      return false;
    }
    const cache = new Map();
    function translate(value) {
      if (!value || typeof value !== 'string') return value;
      const text = normalized(value);
      if (!text) return value;
      if (cache.has(text)) return value.replace(value.trim(), cache.get(text));
      let result = lookup(text);
      if (!result) {
        const duration = x => x.replace(/(\d+)\s*days?/g, '$1 天').replace(/(\d+)\s*hours?/g, '$1 小时').replace(/(\d+)\s*minutes?/g, '$1 分钟').replace(/(\d+)\s*seconds?/g, '$1 秒');
        if (/^You have used some of your (weekly|5-hour) limit, it will fully refresh in .+\.$/.test(text)) result = text.replace(/^You have used some of your (weekly|5-hour) limit, it will fully refresh in (.+)\.$/, (_, period, time) => `已使用部分${period === 'weekly' ? '本周' : '五小时'}配额，将在 ${duration(time)}后完全恢复。`);
        else if (/^Select model, current: /i.test(text)) result = text.replace(/^Select model, current: /i, '选择模型，当前：');
        else if (/^Agent permissions preset selector, current: /.test(text)) result = text.replace(/^Agent permissions preset selector, current: (.*)$/, (_, v) => '智能体权限预设，当前：' + (lookup(v) || v));
        else if (/^No more older messages, showing \d+ of \d+$/.test(text)) result = text.replace(/^No more older messages, showing (\d+) of (\d+)$/, '已加载全部历史消息，显示 $1 / $2 条');
        else if (/^\d+ tasks? running$/.test(text)) result = text.replace(/^(\d+) tasks? running$/, '$1 个任务正在运行');
        else if (/^Thought for \d+[sm]$/.test(text)) result = text.replace(/^Thought for (\d+)([sm])$/, (_, n, u) => `已思考 ${n} ${u === 's' ? '秒' : '分钟'}`);
        else if (/^Worked for \d+[smh]$/.test(text)) result = text.replace(/^Worked for (\d+)([smh])$/, (_, n, u) => `已运行 ${n} ${u === 's' ? '秒' : u === 'm' ? '分钟' : '小时'}`);
        else if (/^(Install|Uninstall|More actions for|See more in) .+$/.test(text)) result = text.replace(/^(Install|Uninstall|More actions for|See more in) (.+)$/, (_, action, name) => ({Install:'安装 ',Uninstall:'卸载 ','More actions for':'更多操作：','See more in':'查看更多：'}[action]) + (lookup(name) || name));
        else if (/^See \d+ more$/.test(text)) result = text.replace(/^See (\d+) more$/, '再看 $1 项');
        else if (/^See \d+ more skills and rules$/.test(text)) result = text.replace(/^See (\d+) more skills and rules$/, '再看 $1 项技能与规则');
        else if (/^\d+ tools? enabled$/.test(text)) result = text.replace(/^(\d+) tools? enabled$/, '已启用 $1 个工具');
        else if (/^Global: Installed in /.test(text)) result = text.replace(/^Global: Installed in /, '全局：安装于 ');
        else if (/^\d{1,2}:\d{2} (AM|PM)$/.test(text)) result = text.replace(/^(\d{1,2}:\d{2}) (AM|PM)$/, (_, time, period) => (period === 'AM' ? '上午 ' : '下午 ') + time);
        else if (/^\d+(s|m|h|d|w|mo)( ago)?$/.test(text)) result = text.replace(/^(\d+)(s|m|h|d|w|mo)( ago)?$/, (_, number, unit, ago) => number + ({s:'秒',m:'分钟',h:'小时',d:'天',w:'周',mo:'个月'}[unit]) + (ago ? '前' : ''));
        else if (/^Show \d+ breakdowns?$/.test(text)) result = text.replace(/^Show (\d+) breakdowns?$/, '显示 $1 项明细');
        else if (/^Permanently delete .+\.$/.test(text)) result = text.replace(/^Permanently delete (.+)\.$/, '永久删除 $1。');
        else if (/^(Send|Cancel) \((?:Ctrl|⌘).+\)$/.test(text)) result = text.replace(/^(Send|Cancel)/, v => lookup(v) || v);
      }
      if (!result) return value;
      if (cache.size > 4096) cache.clear();
      cache.set(text, result);
      return value.replace(value.trim(), result);
    }
    function scan(root, refreshNames = true) {
      if (!root?.isConnected) return;
      if (refreshNames) rememberNames();
      if (root.nodeType === Node.TEXT_NODE) root = root.parentElement;
      if (!root || root.nodeType !== Node.ELEMENT_NODE) return;
      if (root.closest(content + ',' + names)) return;
      const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let node;
      while ((node = walker.nextNode())) {
        const e = node.parentElement;
        if (!e || protectedElement(e)) continue;
        const result = translate(node.nodeValue);
        if (result !== node.nodeValue) node.nodeValue = result;
      }
      const controls = [root, ...root.querySelectorAll('[title],[aria-label],[placeholder],[data-placeholder]')];
      for (const e of controls) {
        if (protectedRoots.has(e) || e.closest(names + ',[data-testid="tool-call-output"],[data-testid="tool-call-command"],[data-testid="artifact-content"],[data-testid="file-content"]')) continue;
        // Attributes of editable controls describe the UI; their values and contents stay intact.
        if (e.closest('pre,code,.monaco-editor,.xterm,.markdown,.prose,[data-testid="user-message-document-chip"],.context-scope-mention,[data-quotable-inline]') || (e.closest('article,[role="article"]') && !e.matches('button,[role="button"]'))) continue;
        for (const attr of ['title', 'aria-label', 'placeholder', 'data-placeholder']) {
          const value = e.getAttribute(attr);
          if (e.closest('article,[role="article"]') && !e.matches(uiInArticle) && !articleLabels.has(value?.trim())) continue;
          const result = translate(value);
          if (value && value !== result) e.setAttribute(attr, result);
        }
      }
    }
    globalThis.__antigravityChineseVersion = 1;
    let scheduled = false;
    const pending = new Set();
    const observer = new MutationObserver(records => {
      for (const record of records) {
        if (record.type === 'childList') for (const node of record.addedNodes) pending.add(node);
        else pending.add(record.target);
      }
      if (scheduled) return;
      scheduled = true;
      // setTimeout also runs in an unfocused window; requestAnimationFrame may stay suspended.
      setTimeout(() => {
        scheduled = false;
        const nodes = [...pending].filter(node => {
          for (let parent = node.parentNode; parent; parent = parent.parentNode) if (pending.has(parent)) return false;
          return true;
        }); pending.clear();
        rememberNames();
        for (const node of nodes) if (node.isConnected) scan(node, false);
      }, 40);
    });
    const observeOptions = {childList:true,subtree:true,characterData:true,attributes:true,
      attributeFilter:['title','aria-label','placeholder','data-placeholder']};
    let observedBody = document.body;
    observer.observe(observedBody, observeOptions);
    scan(observedBody);
    globalThis.__antigravityChineseObserver = observer;
    // SPA navigation and body replacement also occur when the window is unfocused.
    globalThis.__antigravityChineseTimer = setInterval(() => {
      if (document.body && document.body !== observedBody) {
        observer.disconnect(); observedBody = document.body; observer.observe(observedBody, observeOptions);
      }
      scan(document.body);
    }, 2500);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})
