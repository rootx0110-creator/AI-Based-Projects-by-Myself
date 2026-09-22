const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('breachmap', {
  saveTextFile: (payload) => ipcRenderer.invoke('dialog:saveTextFile', payload),
  getVersion: () => ipcRenderer.invoke('app:version')
});