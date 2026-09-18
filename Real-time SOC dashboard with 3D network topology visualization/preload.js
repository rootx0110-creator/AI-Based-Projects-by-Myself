const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('socApp', {
  appName: 'SOC 3D Dashboard',
  versions: {
    electron: process.versions.electron,
    chrome: process.versions.chrome,
    node: process.versions.node
  },
  saveReportHtml: (html, suggestedName) =>
    ipcRenderer.invoke('save-report-html', html, suggestedName)
});