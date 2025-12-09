using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;


// 消息接收动作委托定义
public delegate void MsgRecAction(params object[] _objs);

/// <summary>
/// 消息中心(使用.Instance调用 不是静态类) UI使用的是Signal 
/// 注意：要注意有无参数的区别，无参数的方法以Act为后缀 发送消息时也要注意参数匹配
/// </summary>
public class MsgCenter : SingletonNoMono<MsgCenter>
{
    // 有参事件字典
    private Dictionary<int, List<MsgRecAction>> _m_broadcastDict = new Dictionary<int, List<MsgRecAction>>();

    // 无参事件字典
    private Dictionary<int, List<Action>> _m_broadcastActDict = new Dictionary<int, List<Action>>();

    private List<MsgRecAction> _m_cacheBroadcastList;
    private List<Action> _m_cacheBroadcastActList;

    /// <summary>
    /// 广播事件-无参回调
    /// </summary>
    /// <param name="_msg"></param>
    public static void SendMsgAct(int _msg)
    {
        Instance.sendMsgAct(_msg);
    }

    private void sendMsgAct(int _msg)
    {
        List<Action> srcList;

        if (_m_broadcastActDict.TryGetValue(_msg, out srcList) && srcList.Count > 0)
        {
            if (_m_cacheBroadcastActList == null)
                _m_cacheBroadcastActList = new List<Action>();
            else
                _m_cacheBroadcastActList.Clear();

            _m_cacheBroadcastActList.AddRange(srcList);
            for (int i = 0; i < _m_cacheBroadcastActList.Count; ++i)
            {
                _m_cacheBroadcastActList[i]();
            }
        }
    }

    /// <summary>
    /// 广播事件-有参回调
    /// </summary>
    /// <param name="_msg"></param>
    /// <param name="_obj">可变参数</param>
    public static void SendMsg(int _msg, params object[] _obj)
    {
        Instance.sendMsg(_msg, _obj);
    }

    private void sendMsg(int _msg, params object[] _obj)
    {
        List<MsgRecAction> srcList;
        if (_m_broadcastDict.TryGetValue(_msg, out srcList) && srcList.Count > 0)
        {
            if (_m_cacheBroadcastList == null)
                _m_cacheBroadcastList = new List<MsgRecAction>();
            else
                _m_cacheBroadcastList.Clear();

            _m_cacheBroadcastList.AddRange(srcList);
            for (int i = 0; i < _m_cacheBroadcastList.Count; ++i)
            {
                _m_cacheBroadcastList[i](_obj);
            }
        }
    }

    /// <summary>
    /// 注册事件-无参回调
    /// </summary>
    /// <param name="_msg"></param>
    /// <param name="_callback"></param>
    public static void RegisterMsgAct(int _msg, Action _callback)
    {
        Instance.registerMsgAct(_msg, _callback);
    }

    private void registerMsgAct(int _msg, Action _callback)
    {
        List<Action> broadcast;
        if (!_m_broadcastActDict.TryGetValue(_msg, out broadcast))
        {
            broadcast = new List<Action>();
            _m_broadcastActDict[_msg] = broadcast;
        }

        if (!broadcast.Contains(_callback))
        {
            broadcast.Add(_callback);
        }
    }

    /// <summary>
    /// 注册事件-有参回调
    /// </summary>
    /// <param name="_msg"></param>
    /// <param name="_callback"></param>
    public static void RegisterMsg(int _msg, MsgRecAction _callback)
    {
        Instance.registerMsg(_msg, _callback);
    }

    private void registerMsg(int _msg, MsgRecAction _callback)
    {
        List<MsgRecAction> broadcast;
        if (!_m_broadcastDict.TryGetValue(_msg, out broadcast))
        {
            broadcast = new List<MsgRecAction>();
            _m_broadcastDict[_msg] = broadcast;
        }

        if (!broadcast.Contains(_callback))
        {
            broadcast.Add(_callback);
        }
    }

    /// <summary>
    /// 注销事件-无参回调
    /// </summary>
    /// <param name="_msg"></param>
    /// <param name="_callback"></param>
    public static void UnregisterMsgAct(int _msg, Action _callback)
    {
        Instance.unregisterMsgAct(_msg, _callback);
    }

    private void unregisterMsgAct(int _msg, Action _callback)
    {
        List<Action> broadcast;
        if (!_m_broadcastActDict.TryGetValue(_msg, out broadcast))
        {
            return;
        }

        broadcast.Remove(_callback);
    }

    /// <summary>
    /// 注销事件-有参回调
    /// </summary>
    /// <param name="_msg"></param>
    /// <param name="_callback"></param>
    public static void UnregisterMsg(int _msg, MsgRecAction _callback)
    {
        Instance.unregisterMsg(_msg, _callback);
    }

    private void unregisterMsg(int _msg, MsgRecAction _callback)
    {
        List<MsgRecAction> broadcast;
        if (!_m_broadcastDict.TryGetValue(_msg, out broadcast))
        {
            return;
        }

        broadcast.Remove(_callback);
    }
}