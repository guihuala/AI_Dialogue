import { createApp, ref, computed, onMounted } from 'vue';
import { useTheme } from './composables/useTheme.js';
import { useMonitor } from './composables/useMonitor.js';
import { useIntervention } from './composables/useIntervention.js';
import { useSaves } from './composables/useSaves.js';
import { useCms } from './composables/useCms.js';
import { useSettings } from './composables/useSettings.js';

createApp({
    setup() {
        const currentTab = ref('monitor');
        const toastMsg = ref('');
        const showToast = (msg) => {
            toastMsg.value = msg;
            setTimeout(() => toastMsg.value = '', 3000);
        };

        const tabTitle = computed(() => {
            if (currentTab.value === 'monitor') return '监视中心';
            if (currentTab.value === 'intervention') return '控制权限';
            if (currentTab.value === 'saves') return '快照档案室';
            if (currentTab.value === 'cms') return '资源管理';
            return '参数调优';
        });

        // 引入各大模块
        const themeModule = useTheme();
        const monitorModule = useMonitor(showToast);
        const interventionModule = useIntervention(showToast, monitorModule.monitor);
        const savesModule = useSaves(showToast);
        const cmsModule = useCms(showToast);
        const settingsModule = useSettings(showToast);

        // 统一标签切换与初始化拦截
        const switchTab = (tabName) => {
            currentTab.value = tabName;
            if (tabName === 'intervention') interventionModule.openIntervention();
            if (tabName === 'saves') savesModule.openSaves();
        };

        // 全局初始化
        onMounted(() => {
            cmsModule.fetchFileList();
            settingsModule.fetchSettings();
            setInterval(monitorModule.fetchMonitorData, 3000);
        });

        return {
            currentTab, tabTitle, toastMsg, showToast, switchTab,
            ...themeModule,
            ...monitorModule,
            ...interventionModule,
            ...savesModule,
            ...cmsModule,
            ...settingsModule
        };
    }
}).mount('#app');