using UnityEngine;
using UnityEngine.UI;
using System;
using System.Collections;
using System.Collections.Generic;

namespace SaveSystem
{
    public class SaveView : MonoBehaviour
    {
        [Header("UI Components")]
        [SerializeField] private GameObject loadingIndicator;
        [SerializeField] private Text statusText;
        [SerializeField] private List<Button> slotButtons; 

        // Events
        // public Action<string> OnSlotClicked; // Deprecated by Event Center

        private void Awake()
        {
            // Register Events
            MsgCenter.RegisterMsgAct(MsgConst.MSG_SAVE_LOADING_START, OnLoadingStart);
            MsgCenter.RegisterMsgAct(MsgConst.MSG_SAVE_LOADING_END, OnLoadingEnd);
            MsgCenter.RegisterMsg(MsgConst.MSG_SAVE_MESSAGE_SHOW, OnShowMessage);
        }

        private void OnDestroy()
        {
            // Unregister Events
            MsgCenter.UnregisterMsgAct(MsgConst.MSG_SAVE_LOADING_START, OnLoadingStart);
            MsgCenter.UnregisterMsgAct(MsgConst.MSG_SAVE_LOADING_END, OnLoadingEnd);
            MsgCenter.UnregisterMsg(MsgConst.MSG_SAVE_MESSAGE_SHOW, OnShowMessage);
        }

        private void Start()
        {
            for (int i = 0; i < slotButtons.Count; i++)
            {
                if (slotButtons[i] != null)
                {
                    string id = $"slot_{i+1}";
                    slotButtons[i].onClick.AddListener(() => {
                         // Decoupled Input: Send Event
                         MsgCenter.SendMsg(MsgConst.MSG_SAVE_SLOT_CLICKED, id);
                    });
                }
            }
        }

        // --- Event Handlers ---

        private void OnLoadingStart() => SetLoadingState(true);
        private void OnLoadingEnd() => SetLoadingState(false);
        private void OnShowMessage(params object[] args)
        {
            if (args.Length > 0 && args[0] is string msg) ShowStatusMessage(msg);
        }

        // --- UI Logic ---

        public void SetLoadingState(bool isLoading)
        {
            if (loadingIndicator != null) loadingIndicator.SetActive(isLoading);
        }

        public void ShowStatusMessage(string message)
        {
            if (statusText != null) 
            {
                statusText.text = message;
                statusText.gameObject.SetActive(true);
                StartCoroutine(HideStatusDelay());
            }
            else
            {
                Debug.Log($"[SaveView] {message}");
            }
        }

        private IEnumerator HideStatusDelay()
        {
            yield return new WaitForSeconds(3f);
            if (statusText != null) statusText.gameObject.SetActive(false);
        }
    }
}
