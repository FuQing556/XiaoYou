// 小悠 v2 — Preload IPC 桥接
const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  onShortcut: (callback) => {
    ipcRenderer.on('shortcut', (event, action) => callback(action));
  },
  onScaleChanged: (callback) => {
    ipcRenderer.on('scale-changed', (event, scale) => callback(scale));
  },
  sendToBackend: (msg) => ipcRenderer.invoke('send-to-backend', msg),
});
