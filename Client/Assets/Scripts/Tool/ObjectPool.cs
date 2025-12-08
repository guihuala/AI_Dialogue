using System.Collections.Generic;
using UnityEngine;

public class ObjectPool : Singleton<ObjectPool>
{
    // 字典：Key是Prefab的引用，Value是这个Prefab对应的闲置队列
    private Dictionary<GameObject, Queue<GameObject>> poolDictionary = new Dictionary<GameObject, Queue<GameObject>>();

    // 从池子里取东西
    public GameObject Spawn(GameObject prefab, Transform parent)
    {
        if (!poolDictionary.ContainsKey(prefab))
        {
            poolDictionary[prefab] = new Queue<GameObject>();
        }

        GameObject obj;

        if (poolDictionary[prefab].Count > 0)
        {
            // 1. 从队列里取出一个闲置的
            obj = poolDictionary[prefab].Dequeue();
            obj.SetActive(true);
            obj.transform.SetParent(parent, false); // 重新挂载到父节点
            obj.transform.SetAsLastSibling(); // 放到最下面
        }
        else
        {
            // 2. 队列空了，只能实例化一个新的
            obj = Instantiate(prefab, parent);
        }

        return obj;
    }

    // 把用完的东西还回池子
    public void Despawn(GameObject obj, GameObject prefab)
    {
        obj.SetActive(false); // 隐藏
        
        // 简单处理：为了不让 Hierarchy 乱，可以把回收的物体挂在 Pool 下面，或者留在原地隐藏
        // 挂在 Pool 下面会让 ScrollView 的 Layout 计算量减少
        obj.transform.SetParent(this.transform, false); 

        if (!poolDictionary.ContainsKey(prefab))
        {
            poolDictionary[prefab] = new Queue<GameObject>();
        }

        poolDictionary[prefab].Enqueue(obj);
    }
}