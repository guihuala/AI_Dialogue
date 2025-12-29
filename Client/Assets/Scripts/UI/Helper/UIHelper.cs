using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace SimpleUITips
{
    #region Public Models

    public enum FixedUIPosType
    {
        Left,
        Right,
        Top,
        Bottom,
        Center
    }

    public enum CircleProgressType
    {
        Auto,
        Manual,
    }

    /// <summary>
    /// 氣泡信息
    /// </summary>
    public class BubbleInfo : IComparable<BubbleInfo>
    {
        public List<string> actionKeys;     // 交互键位显示（如："E"、"F"、"Space"）
        public GameObject creator;          // 谁创建了气泡（世界坐标跟随）
        public GameObject player;           // 用于排序（距离 player 最近者优先）
        public string content;              // 气泡内容
        public string itemName;             // 物体名

        public BubbleInfo(List<string> actionKeys, GameObject creator, GameObject player, string content, string itemName)
        {
            this.actionKeys = actionKeys;
            this.creator = creator;
            this.player = player;
            this.content = content;
            this.itemName = itemName;
        }

        public int CompareTo(BubbleInfo other)
        {
            if (creator == null || player == null) return 1;
            if (other == null || other.creator == null || other.player == null) return -1;
            float myDist = Vector3.Distance(creator.transform.position, player.transform.position);
            float otherDist = Vector3.Distance(other.creator.transform.position, other.player.transform.position);
            return myDist <= otherDist ? -1 : 1;
        }
    }

    /// <summary>
    /// 飘字提示信息
    /// </summary>
    public class TipInfo
    {
        public string content;
        public Vector3 worldPos;
        public float showTime; // 停留时长

        public TipInfo(string content, Vector3 worldPos, float showTime = 0.75f)
        {
            this.content = content;
            this.worldPos = worldPos;
            this.showTime = showTime;
        }
    }

    /// <summary>
    /// 图标提示信息
    /// </summary>
    public class SignInfo
    {
        public string signIconPath; // Resources 下的路径
        public GameObject creator;  // 跟随对象
        public float showTime;

        public SignInfo(string signIconPath, GameObject creator, float showTime = 0.75f)
        {
            this.signIconPath = signIconPath;
            this.creator = creator;
            this.showTime = showTime;
        }
    }

    #endregion

    #region UI Items

    internal static class UIConvert
    {
        public static Vector2 ScreenToUIPoint(RectTransform anyChildRt, Vector2 screenPos)
        {
            if (anyChildRt == null) return Vector2.zero;
            var parent = anyChildRt.parent as RectTransform;
            if (parent == null) return Vector2.zero;
            RectTransformUtility.ScreenPointToLocalPointInRectangle(parent, screenPos, GetUICamera(parent), out var lp);
            return lp;
        }

        public static Camera GetUICamera(Transform t)
        {
            var canvas = t.GetComponentInParent<Canvas>();
            if (canvas == null) return Camera.main;
            if (canvas.renderMode == RenderMode.ScreenSpaceCamera || canvas.renderMode == RenderMode.WorldSpace)
                return canvas.worldCamera != null ? canvas.worldCamera : Camera.main;
            return null; // ScreenSpaceOverlay
        }
    }

    #endregion
    
    public class UIHelper : SingletonPersistent<UIHelper>
    {
        [Header("Bubble")]
        public GameObject BubblePrefab;

        private GameObject _currentBubble;
        private BubbleInfo _currentBubbleInfo;
        public readonly List<BubbleInfo> BubbleList = new List<BubbleInfo>();

        [Header("Tip")]
        public GameObject TipPrefab;
        public float ShowTipInterval = 0.15f;
        public float QuickReplaceThreshold = 0.3f;
        private readonly Queue<TipInfo> _tipQueue = new Queue<TipInfo>();
        private GameObject _currentTipGO;
        private float _lastTipShowTime;

        [Header("Sign")]
        public GameObject SignPrefab;

        [Header("FixedPos")]
        public GameObject FixedPosTextPrefab;

        [Header("Progress")]
        public GameObject CircleProgressPrefab;
        private readonly Dictionary<string, GameObject> _circleProgressDict = new Dictionary<string, GameObject>();

        #region Bubble API

        private void RefreshBubble()
        {
            if (BubbleList == null || BubbleList.Count == 0) return;

            var tmp = BubbleList[0];
            if (_currentBubbleInfo != null && tmp.creator == _currentBubbleInfo.creator) return;

            if (_currentBubble != null) DestroyBubble();

            _currentBubbleInfo = tmp;
            _currentBubble = Instantiate(BubblePrefab, transform, false);

            var bubbleItem = _currentBubble.GetComponent<UIBubbleItem>();
            string keyStr = string.Empty;
            if (tmp.actionKeys != null && tmp.actionKeys.Count > 0)
                keyStr = string.Join("/", tmp.actionKeys);
            if (bubbleItem != null)
                bubbleItem.Init(tmp, keyStr);
        }

        public void DestroyBubble()
        {
            if (_currentBubble)
            {
                var it = _currentBubble.GetComponent<UIBubbleItem>();
                if (it != null) it.DestroyBubble();
                else Destroy(_currentBubble);
                _currentBubble = null;
                _currentBubbleInfo = null;
            }
        }

        public void AddBubble(BubbleInfo info)
        {
            if (info == null || info.creator == null) return;
            if (BubbleList.Exists(x => x.creator == info.creator)) return;
            BubbleList.Add(info);
            BubbleList.Sort();
            RefreshBubble();
        }

        public void RemoveBubble(GameObject creator)
        {
            if (creator == null) return;
            var idx = BubbleList.FindIndex(x => x.creator == creator);
            if (idx >= 0) BubbleList.RemoveAt(idx);
            if (BubbleList.Count == 0) DestroyBubble();
            else RefreshBubble();
        }

        public void UpdateBubbleContent(GameObject creator, string content)
        {
            if (creator == null || string.IsNullOrEmpty(content)) return;
            var info = BubbleList.Find(x => x.creator == creator);
            if (info == null) return;
            info.content = content;
            if (_currentBubble != null)
            {
                var it = _currentBubble.GetComponent<UIBubbleItem>();
                if (it != null) it.UpdateContent(content);
            }
        }

        public void SortBubbleByDistance()
        {
            if (BubbleList == null || BubbleList.Count == 0) return;
            var oldNearest = BubbleList[0];
            BubbleList.Sort();
            if (oldNearest != BubbleList[0]) RefreshBubble();
        }

        #endregion

        #region Tip API

        public void ShowTip(TipInfo tip)
        {
            float now = Time.time;
            float delta = now - _lastTipShowTime;

            if (delta <= QuickReplaceThreshold && _currentTipGO != null)
            {
                var item = _currentTipGO.GetComponent<UITipItem>();
                if (item != null)
                {
                    item.ResetTip(tip.worldPos, tip.content);
                    _lastTipShowTime = now;
                    return;
                }
            }

            _tipQueue.Enqueue(tip);
            StopCoroutine(nameof(ShowTipCoroutine));
            StartCoroutine(nameof(ShowTipCoroutine));
        }

        private IEnumerator ShowTipCoroutine()
        {
            while (_tipQueue.Count > 0)
            {
                var info = _tipQueue.Dequeue();
                _lastTipShowTime = Time.time;
                _currentTipGO = Instantiate(TipPrefab, transform, false);
                var it = _currentTipGO.GetComponent<UITipItem>();
                if (it != null) it.Init(info.worldPos, info.content, info.showTime);
                yield return new WaitForSeconds(ShowTipInterval);
            }
        }

        #endregion

        #region Sign API

        public void ShowSign(SignInfo sign)
        {
            var go = Instantiate(SignPrefab, transform, false);
            var it = go.GetComponent<UISignItem>();
            if (it != null) it.Init(sign.creator, sign.signIconPath);
            Destroy(go, sign.showTime);
        }

        #endregion

        #region FixedPos API

        public void ShowFixedText(FixedUIPosType pos, string content, float lifeTime)
        {
            var go = Instantiate(FixedPosTextPrefab, transform, false);
            var it = go.GetComponent<UIFixedPosTextItem>();
            if (it != null) it.Init(pos, content);
            Destroy(go, lifeTime);
        }

        #endregion

        #region Progress API

        public void ShowCircleProgress(string key, CircleProgressType type, GameObject creator, float duration = 0f)
        {
            if (string.IsNullOrEmpty(key) || creator == null) return;
            if (_circleProgressDict.ContainsKey(key)) return;
            var go = Instantiate(CircleProgressPrefab, transform, false);
            var it = go.GetComponent<UICommonProgressItem>();
            if (it != null)
            {
                it.Init(key, type, creator, duration, () => { _circleProgressDict.Remove(key); });
                _circleProgressDict[key] = go;
            }
            else
            {
                Destroy(go);
            }
        }

        public void SetCircleProgress01(string key, float value01)
        {
            if (!_circleProgressDict.TryGetValue(key, out var go) || go == null) return;
            var it = go.GetComponent<UICommonProgressItem>();
            if (it != null) it.SetManualProgress01(value01);
        }

        public void DestroyCircleProgress(string key)
        {
            if (!_circleProgressDict.ContainsKey(key)) return;
            if (_circleProgressDict[key] != null) Destroy(_circleProgressDict[key]);
            _circleProgressDict.Remove(key);
        }

        #endregion
    }
}
