using System.Collections.Generic;
using UnityEngine;

public class ObjectPool : Singleton<ObjectPool>
{
    // 对象池字典：Key=物体名称, Value=对象队列
    private Dictionary<string, Queue<GameObject>> objectPool = new Dictionary<string, Queue<GameObject>>();
    
    // 层级缓存字典：Key=物体名称, Value=对应的父节点Transform (避免频繁 GameObject.Find)
    private Dictionary<string, Transform> poolParents = new Dictionary<string, Transform>();
    
    // 总父节点
    private GameObject rootPool;

    /// <summary>
    /// 从池中获取对象
    /// </summary>
    public GameObject GetObject(GameObject prefab)
    {
        GameObject obj;
        // 使用 prefab 的名字作为 Key (不含 Clone)
        string keyName = prefab.name;

        // 1. 尝试从池中取
        if (objectPool.ContainsKey(keyName) && objectPool[keyName].Count > 0)
        {
            obj = objectPool[keyName].Dequeue();
        }
        else
        {
            // 2. 池中没有，实例化一个新的
            obj = Instantiate(prefab);
            // 关键优化：实例化时直接改名，去掉 "(Clone)"
            // 这样回收时直接取 obj.name 即可，不用做字符串 Replace 操作
            obj.name = keyName; 
            
            // 设置父节点整理层级
            SetObjectParent(obj, keyName);
        }

        // 激活并返回
        obj.SetActive(true);
        return obj;
    }

    /// <summary>
    /// 将对象回收进池子
    /// </summary>
    public void PushObject(GameObject obj)
    {
        if (obj == null) return;

        // 直接使用名字作为 Key (因为生成时已经去掉了 Clone)
        string keyName = obj.name;

        // 确保字典中有这个 Key 的记录
        if (!objectPool.ContainsKey(keyName))
        {
            objectPool.Add(keyName, new Queue<GameObject>());
        }

        // 加入队列
        objectPool[keyName].Enqueue(obj);
        
        // 设为不激活
        obj.SetActive(false);
        
        // 可选：回收时归位父节点（防止物体在外面乱跑）
        SetObjectParent(obj, keyName);
    }

    /// <summary>
    /// 清空对象池 (切换场景时可能需要)
    /// </summary>
    public void Clear()
    {
        objectPool.Clear();
        poolParents.Clear();
        // 注意：这里只是清空引用，如果场景被销毁，物体会自动销毁。
        // 如果是 DontDestroyOnLoad 的池子，需要手动 Destroy 所有物体。
    }

    /// <summary>
    /// 内部方法：设置层级父节点
    /// </summary>
    private void SetObjectParent(GameObject obj, string keyName)
    {
        // 如果总父节点被销毁了（比如场景切换），重建一个
        if (rootPool == null) rootPool = new GameObject("ObjectPool");

        // 检查是否已经有对应的子池父节点
        if (!poolParents.TryGetValue(keyName, out Transform parentTrans))
        {
            // 如果没有，创建一个新的 GameObject 作为该类物体的父节点
            GameObject childPool = new GameObject(keyName + "Pool");
            childPool.transform.SetParent(rootPool.transform);
            parentTrans = childPool.transform;
            
            // 存入缓存
            poolParents.Add(keyName, parentTrans);
        }

        // 设置父子关系
        obj.transform.SetParent(parentTrans);
    }
}