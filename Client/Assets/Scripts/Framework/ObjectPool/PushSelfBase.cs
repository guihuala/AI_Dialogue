using UnityEngine;

public class PushSelfBase : MonoBehaviour
{
    [SerializeField] private float lifeTime = 3f;
    private float timer;

    // 使用 OnEnable 而不是 Start 或 InitPushTimer
    // 每次对象从池里被取出来(SetActive true)时，都会自动调用 OnEnable
    private void OnEnable()
    {
        timer = 0f;
    }

    void Update()
    {
        timer += Time.deltaTime;

        if (timer > lifeTime)
        {
            PushObj();
        }
    }

    private void PushObj()
    {
        // 增加判空，防止游戏退出时单例已销毁报错
        if (ObjectPool.Instance != null)
        {
            ObjectPool.Instance.PushObject(gameObject);
        }
    }
}