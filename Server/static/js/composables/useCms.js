import { ref, computed } from 'vue';

export function useCms(showToast) {
    const cmsType = ref('md');
    const fileList = ref({ md: [], csv: [] });
    const cmsActiveFile = ref('');
    const cmsContent = ref('');
    const viewMode = ref('raw');
    const parsedCsv = ref([]);

    // ==========================================
    // 🌟 新增：事件表单的相关状态
    // ==========================================
    const showEventForm = ref(false);
    const eventForm = ref({
        poolFile: '04_条件触发.csv', // 默认选中条件触发池
        Event_ID: '',
        事件标题: '',
        所属章节: 1,
        事件类型: '',
        是否Boss: 'FALSE',
        触发条件: '',
        专属角色: '',
        场景与冲突描述: '',
        潜在冲突点: '',
        玩家交互: '',
        结果: ''
    });

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
        } else {
            cmsContent.value = window.Papa.unparse(parsedCsv.value);
        }
        viewMode.value = mode;
    };

    const addRow = () => {
        const colCount = parsedCsv.value[0] ? parsedCsv.value[0].length : 2;
        parsedCsv.value.push(new Array(colCount).fill(''));
    };

    const removeRow = (index) => {
        parsedCsv.value.splice(index, 1);
    };

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
            if (cmsType.value === 'csv') {
                viewMode.value = 'raw';
                toggleView('table');
            } else {
                viewMode.value = 'raw';
            }
        } catch (e) {
            showToast("读取文件失败");
        }
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
        } catch (e) {
            showToast("执行写入失败");
        }
    };

    const triggerRebuild = async () => {
        try {
            showToast("正在向引擎注入新数据...");
            const res = await fetch('/api/system/rebuild_knowledge', { method: 'POST' });
            const data = await res.json();
            if (data.status === 'success') showToast("热重载完毕");
            else showToast("执行拒绝：" + data.message);
        } catch (e) {
            showToast("通信异常，重载失败");
        }
    };

    // ==========================================
    // 🌟 新增：提交事件表单的核心方法
    // ==========================================
    const submitEventForm = async () => {
        if (!eventForm.value.Event_ID) {
            showToast('⚠️ Event_ID 不能为空！');
            return;
        }
        try {
            const response = await fetch('/api/admin/events/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(eventForm.value)
            });
            const result = await response.json();

            if (result.success) {
                showEventForm.value = false; // 关闭弹窗
                showToast('✅ 事件已成功写入目标池！');

                // 如果当前正好在看这个文件，自动刷新一下视图
                if (cmsType.value === 'csv' && cmsActiveFile.value === eventForm.value.poolFile) {
                    loadFile(cmsActiveFile.value);
                }
            } else {
                showToast('❌ 保存失败: ' + result.error);
            }
        } catch (err) {
            showToast('❌ 网络请求出错，请检查后端');
            console.error(err);
        }
    };

    // 🌟 在 return 中暴露新增的变量和方法
    return {
        cmsType, fileList, cmsActiveFile, cmsContent, viewMode, parsedCsv, groupedMdFiles,
        showEventForm, eventForm, // 暴露表单状态
        getFileName, toggleView, addRow, removeRow, addColumn, changeCmsType, fetchFileList, loadFile, saveFile, triggerRebuild,
        submitEventForm // 暴露提交方法
    };
}