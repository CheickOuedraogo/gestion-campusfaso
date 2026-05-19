const { contextBridge, ipcRenderer, webUtils } = require('electron');

contextBridge.exposeInMainWorld('api', {
  openFile:        ()           => ipcRenderer.invoke('file:open'),
  openMultiple:    ()           => ipcRenderer.invoke('file:openMultiple'),
  loadFile:        (fp)         => ipcRenderer.invoke('file:load', fp),
  basename:        (fp)         => ipcRenderer.invoke('file:basename', fp),
  getPathForFile:  (file)       => webUtils.getPathForFile(file),
  dryRun:          (payload)    => ipcRenderer.invoke('transfer:dryRun', payload),
  commit:          (results)    => ipcRenderer.invoke('transfer:commit', results),
});
