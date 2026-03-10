import { ref, computed } from 'vue';

export function useCms(showToast) {
    const cmsType = ref('md');
    const fileList = ref({ md: [], csv: [] });
    const cmsActiveFile = ref('');
    const cmsContent = ref('');
    const viewMode = ref('raw');
    const parsedCsv = ref([]);

    const groupedMdFiles = computed(() => {
        const groups = {};
        fileList.value.md.forEach(file => {
            const parts = file.split('/');
            const folder = parts.length > 1 ? parts[0] : '根节点';
            if (!groups[folder]) groups[folder] = [];
            groups[folder].push(file);
        });
        return groups;
    });

    const getFileName = (path) => {
        if (!path) return '';
        const parts = path.split('/');
        return parts[parts.length - 1];
    };

    const toggleView = (mode) => {
        if (mode === viewMode.value) return;
        if (mode === 'table') {
            const parsed = window.Papa.parse(cmsContent.value || '');
            let data = parsed.data || [];
            if (data.length > 0 && data[data.length - 1].length === 1 && data[data.length - 1][0] === '') data.pop();
            if (data.length === 0) data = [['键名1', '键名2']];
            parsedCsv.value = data;
        } else { cmsContent.value = window.Papa.unparse(parsedCsv.value); }
        viewMode.value = mode;
    };

    const addRow = () => {
        const colCount = parsedCsv.value[0] ? parsedCsv.value[0].length : 2;
        parsedCsv.value.push(new Array(colCount).fill(''));
    };
    const removeRow = (index) => { parsedCsv.value.splice(index, 1); };
    const addColumn = () => {
        if (parsedCsv.value.length === 0) return parsedCsv.value = [['新列']];
        parsedCsv.value[0].push('新列');
        for (let i = 1; i < parsedCsv.value.length; i++) parsedCsv.value[i].push('');
    };

    const changeCmsType = (type) => {
        cmsType.value = type;
        cmsActiveFile.value = '';
        cmsContent.value = '';
        viewMode.value = type === 'csv' ? 'table' : 'raw';
    };

    const fetchFileList = async () => {
        try {
            const res = await fetch('/api/admin/files');
            const data = await res.json();
            if (data.status === 'success') fileList.value = { md: data.md, csv: data.csv };
        } catch (e) { }
    };

    const loadFile = async (fileName) => {
        cmsActiveFile.value = fileName;
        try {
            const res = await fetch(`/api/admin/file?type=${cmsType.value}&name=${encodeURIComponent(fileName)}`);
            const data = await res.json();
            cmsContent.value = data.content || '';
            if (cmsType.value === 'csv') { viewMode.value = 'raw'; toggleView('table'); } else { viewMode.value = 'raw'; }
        } catch (e) { showToast("读取文件失败"); }
    };

    const saveFile = async () => {
        if (!cmsActiveFile.value) return;
        if (cmsType.value === 'csv' && viewMode.value === 'table') cmsContent.value = window.Papa.unparse(parsedCsv.value);
        try {
            const res = await fetch('/api/admin/file', {
                method: 'POST', headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: cmsType.value, name: cmsActiveFile.value, content: cmsContent.value })
            });
            if ((await res.json()).status === 'success') showToast(`${cmsActiveFile.value} 数据已写入`);
        } catch (e) { showToast("执行写入失败"); }
    };

    const triggerRebuild = async () => {
        try {
            showToast("正在向引擎注入新数据...");
            const res = await fetch('/api/system/rebuild_knowledge', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') showToast("热重载完毕");
            else showToast("执行拒绝：" + data.message);
        } catch (e) { showToast("通信异常，重载失败"); }
    };

    return { cmsType, fileList, cmsActiveFile, cmsContent, viewMode, parsedCsv, groupedMdFiles, getFileName, toggleView, addRow, removeRow, addColumn, changeCmsType, fetchFileList, loadFile, saveFile, triggerRebuild };
}