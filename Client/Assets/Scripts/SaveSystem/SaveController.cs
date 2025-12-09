using UnityEngine;
using UnityEngine.SceneManagement;
using System.Threading.Tasks;
using System.Collections.Generic;

namespace SaveSystem
{
    public class SaveController : MonoBehaviour
    {
        [Header("MVC Components")]
        // [SerializeField] private SaveView view; // Decoupled
        private SaveModel _model = new SaveModel(); 

        [Header("Dependencies")]
        [SerializeField] private LLMClient llmClient;

        [Header("Configuration")]
        [SerializeField] private string nextSceneName = "GameScene";

        private void Awake()
        {
            MsgCenter.RegisterMsg(MsgConst.MSG_SAVE_SLOT_CLICKED, HandleSlotClicked);
        }

        private void OnDestroy()
        {
            MsgCenter.UnregisterMsg(MsgConst.MSG_SAVE_SLOT_CLICKED, HandleSlotClicked);
        }

        private void Start()
        {
            InitializeSession();
        }

        private void HandleSlotClicked(params object[] args)
        {
            if (args.Length > 0 && args[0] is string slotId)
            {
                OnSlotSelected(slotId);
            }
        }

        public void InitializeSession()
        {
            string sessionId = PlayerPrefs.GetString("CurrentSessionID", "default");
            _model.SetSessionId(sessionId);
            
            if (llmClient != null)
            {
                llmClient.SetSessionId(sessionId);
            }
        }

        // --- Actions ---

        public void OnSlotSelected(string slotId)
        {
            if (string.IsNullOrEmpty(slotId)) slotId = System.Guid.NewGuid().ToString();
            
            PlayerPrefs.SetString("CurrentSessionID", slotId);
            PlayerPrefs.Save();
            
            MsgCenter.SendMsg(MsgConst.MSG_SAVE_MESSAGE_SHOW, $"Selected Slot: {slotId}");
            
            SceneManager.LoadScene(nextSceneName);
        }

        // --- Save / Load Logic ---

        public async Task<bool> SaveGameAsync(float money, float sanity, float gpa, int day, int timeIndex, List<ChatMessage> history)
        {
            MsgCenter.SendMsgAct(MsgConst.MSG_SAVE_LOADING_START);

            // 1. Update Model
            _model.UpdateData(money, sanity, gpa, day, timeIndex, history);

            // 2. Serialize
            string json = _model.ToJson();

            // 3. Send to Server
            bool success = false;
            if (llmClient != null)
            {
                success = await llmClient.SaveGameAsync(json);
            }

            MsgCenter.SendMsgAct(MsgConst.MSG_SAVE_LOADING_END);
            MsgCenter.SendMsg(MsgConst.MSG_SAVE_MESSAGE_SHOW, success ? "Game Saved" : "Save Failed");

            return success;
        }

        public async Task<SaveModel.SaveData> LoadGameAsync()
        {
            MsgCenter.SendMsgAct(MsgConst.MSG_SAVE_LOADING_START);

            // 1. Fetch from Server
            string json = null;
            if (llmClient != null)
            {
                json = await llmClient.LoadGameAsync();
            }
            
            MsgCenter.SendMsgAct(MsgConst.MSG_SAVE_LOADING_END);

            if (!string.IsNullOrEmpty(json))
            {
                // 2. Update Model
                _model.FromJson(json);
                return _model.CurrentData;
            }

            return null;
        }
    }
}
