// 小悠 v2 — Electron 主进程
const { app, BrowserWindow, globalShortcut, screen, ipcMain } = require('electron');
const path = require('path');
const fs = require('fs');

// 日志文件
const LOG = path.join(app.getPath('userData'), 'xiaoyou_renderer.log');

let win = null;
let scaleIndex = 2;
const SCALES = [0.6, 0.8, 1.0, 1.2, 1.5, 2.0];
const BASE_W = 500;
const BASE_H = 620;

function getScale() { return SCALES[scaleIndex] || 1.0; }

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try { fs.appendFileSync(LOG, line); } catch(e) {}
  console.log(msg);
}

function createWindow() {
  const s = getScale();
  const primary = screen.getPrimaryDisplay();
  const workArea = primary.workArea;
  const bounds = primary.bounds;
  const taskbarHeight = bounds.height - workArea.height;

  win = new BrowserWindow({
    width: Math.round(BASE_W * s),
    height: Math.round(BASE_H * s),
    x: workArea.width - Math.round(BASE_W * s) - 20,
    y: workArea.height - Math.round(BASE_H * s) - taskbarHeight,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    resizable: false,
    skipTaskbar: true,
    hasShadow: false,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    },
  });

  // 捕获渲染进程日志
  win.webContents.on('console-message', (event, level, message, line, sourceId) => {
    const prefix = ['VERBOSE','INFO','WARN','ERROR'][level] || 'LOG';
    log(`[renderer ${prefix}] ${message}  (${sourceId}:${line})`);
  });

  // 捕获未处理异常
  win.webContents.on('render-process-gone', (event, details) => {
    log(`[FATAL] Render process gone: reason=${details.reason} exitCode=${details.exitCode}`);
  });

  // 捕获页面加载错误
  win.webContents.on('did-fail-load', (event, code, desc, url) => {
    log(`[FATAL] Page load failed: ${code} ${desc} (${url})`);
  });

  // 页面加载完成
  win.webContents.on('did-finish-load', () => {
    log('[OK] Page loaded');
  });

  win.loadFile('frontend/renderer.html');
  win.setAlwaysOnTop(true, 'normal');
  screen.on('display-metrics-changed', repositionWindow);
  win.on('closed', () => { win = null; });
}

function repositionWindow() {
  if (!win) return;
  const s = getScale();
  const primary = screen.getPrimaryDisplay();
  const workArea = primary.workArea;
  const bounds = primary.bounds;
  const taskbarHeight = bounds.height - workArea.height;
  win.setSize(Math.round(BASE_W * s), Math.round(BASE_H * s));
  win.setPosition(
    workArea.width - Math.round(BASE_W * s) - 20,
    workArea.height - Math.round(BASE_H * s) - taskbarHeight,
  );
}

function applyScale() {
  if (!win) return;
  const s = getScale();
  win.setSize(Math.round(BASE_W * s), Math.round(BASE_H * s));
  repositionWindow();
  win.webContents.send('scale-changed', s);
}

function registerShortcuts() {
  // 模式 — 各自独立
  globalShortcut.register('CommandOrControl+Shift+1', () => { win?.webContents.send('shortcut', 'mode-quiet'); });
  globalShortcut.register('CommandOrControl+Shift+2', () => { win?.webContents.send('shortcut', 'mode-balanced'); });
  globalShortcut.register('CommandOrControl+Shift+3', () => { win?.webContents.send('shortcut', 'mode-chatty'); });
  globalShortcut.register('CommandOrControl+Shift+4', () => { win?.webContents.send('shortcut', 'mode-sweet'); });

  // 表情
  globalShortcut.register('CommandOrControl+Shift+Z', () => { win?.webContents.send('shortcut', 'expr-neutral'); });
  globalShortcut.register('CommandOrControl+Shift+X', () => { win?.webContents.send('shortcut', 'expr-star'); });
  globalShortcut.register('CommandOrControl+Shift+C', () => { win?.webContents.send('shortcut', 'expr-blush'); });
  globalShortcut.register('CommandOrControl+Shift+V', () => { win?.webContents.send('shortcut', 'expr-dizzy'); });

  // 动作
  globalShortcut.register('CommandOrControl+Shift+Q', () => { win?.webContents.send('shortcut', 'act-nod'); });
  globalShortcut.register('CommandOrControl+Shift+W', () => { win?.webContents.send('shortcut', 'act-tilt'); });
  globalShortcut.register('CommandOrControl+Shift+E', () => { win?.webContents.send('shortcut', 'act-wink'); });
  globalShortcut.register('CommandOrControl+Shift+R', () => { win?.webContents.send('shortcut', 'act-excited'); });
  globalShortcut.register('CommandOrControl+Shift+T', () => { win?.webContents.send('shortcut', 'act-sad'); });
  globalShortcut.register('CommandOrControl+Shift+Y', () => { win?.webContents.send('shortcut', 'act-playful'); });

  globalShortcut.register('CommandOrControl+Shift+H', () => { win?.isVisible() ? win.hide() : win?.show(); });
  globalShortcut.register('CommandOrControl+Shift+M', () => { win?.webContents.send('shortcut', 'toggle-mute'); });
  globalShortcut.register('CommandOrControl+Shift+Up', () => { if (scaleIndex < SCALES.length - 1) { scaleIndex++; applyScale(); } });
  globalShortcut.register('CommandOrControl+Shift+Down', () => { if (scaleIndex > 0) { scaleIndex--; applyScale(); } });
  globalShortcut.register('CommandOrControl+Shift+D', () => { win?.webContents.openDevTools({ mode: 'detach' }); });
  globalShortcut.register('CommandOrControl+Shift+F5', () => { win?.webContents.reload(); });
  globalShortcut.register('CommandOrControl+Shift+Escape', () => { app.quit(); });
}

ipcMain.handle('send-to-backend', async () => ({ ok: true }));

const isDev = process.argv.includes('--dev');

ipcMain.handle('screenshot', async () => {
  if (!win) return null;
  const img = await win.webContents.capturePage();
  return img.toDataURL();
});

app.whenReady().then(() => {
  log('[START] XiaoYou v2 launching...');
  log(`[START] Project dir: ${__dirname}`);
  log(`[START] Renderer: ${path.join(__dirname, 'frontend', 'renderer.html')}`);
  log(`[START] exists: ${fs.existsSync(path.join(__dirname, 'frontend', 'renderer.html'))}`);
  createWindow();
  if (isDev) {
    win?.webContents.openDevTools({ mode: 'detach' });
  }
  registerShortcuts();
});

app.on('window-all-closed', () => {
  log('[STOP] Window closed');
  globalShortcut.unregisterAll();
  app.quit();
});

app.on('will-quit', () => {
  log('[STOP] App quitting');
  globalShortcut.unregisterAll();
});

app.on('activate', () => {
  if (win === null) createWindow();
});
