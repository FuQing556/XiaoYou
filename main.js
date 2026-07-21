// 小悠 v2 — Electron 主进程
const { app, BrowserWindow, globalShortcut, screen, ipcMain } = require('electron');
const path = require('path');

let win = null;
let scaleIndex = 2;  // 对应 1.0x
const SCALES = [0.6, 0.8, 1.0, 1.2, 1.5, 2.0];
const BASE_W = 500;
const BASE_H = 620;

function getScale() { return SCALES[scaleIndex] || 1.0; }

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

  win.loadFile('frontend/renderer.html');
  win.setAlwaysOnTop(true, 'normal');  // 低于任务栏

  // 监听任务栏变化
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
  // 模式切换
  globalShortcut.register('CommandOrControl+Shift+Y', () => {
    win?.webContents.send('shortcut', 'cycle-mode');
  });

  // 隐藏/显示
  globalShortcut.register('CommandOrControl+Shift+H', () => {
    if (win?.isVisible()) win.hide();
    else win?.show();
  });

  // 静音
  globalShortcut.register('CommandOrControl+Shift+M', () => {
    win?.webContents.send('shortcut', 'toggle-mute');
  });

  // 缩放
  globalShortcut.register('CommandOrControl+Shift+Up', () => {
    if (scaleIndex < SCALES.length - 1) { scaleIndex++; applyScale(); }
  });
  globalShortcut.register('CommandOrControl+Shift+Down', () => {
    if (scaleIndex > 0) { scaleIndex--; applyScale(); }
  });

  // 模式左右导航
  globalShortcut.register('CommandOrControl+Shift+Left', () => {
    win?.webContents.send('shortcut', 'mode-prev');
  });
  globalShortcut.register('CommandOrControl+Shift+Right', () => {
    win?.webContents.send('shortcut', 'mode-next');
  });

  // 调试
  globalShortcut.register('CommandOrControl+Shift+D', () => {
    win?.webContents.openDevTools({ mode: 'detach' });
  });

  // 重载
  globalShortcut.register('CommandOrControl+Shift+R', () => {
    win?.webContents.reload();
  });

  // 退出
  globalShortcut.register('CommandOrControl+Shift+Q', () => {
    app.quit();
  });
}

// IPC: 前端请求后端指令
ipcMain.handle('send-to-backend', async (event, msg) => {
  // 前端通过 WebSocket 直连后端，此 IPC 保留备用
  return { ok: true };
});

app.whenReady().then(() => {
  createWindow();
  registerShortcuts();
});

app.on('window-all-closed', () => {
  globalShortcut.unregisterAll();
  app.quit();
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});

app.on('activate', () => {
  if (win === null) createWindow();
});
