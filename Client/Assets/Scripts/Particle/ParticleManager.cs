using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

[Serializable]
public class ParticleData
{
    public string effectName;
    public string effectPath;
}

[Serializable]
public class ParticleInfo
{
    public string effectName;
    public ParticleSystem particleSystem;
    public Coroutine autoDestroyCoroutine;
}

public class ParticleManager : SingletonPersistent<ParticleManager>
{
    public List<ParticleInfo> activeParticleEffects = new List<ParticleInfo>();
    public ParticleDatas particleDatas;
    private GameObject _particleRootGO;

    protected override void Awake()
    {
        base.Awake();

        _particleRootGO = new GameObject("PARTICLE_ROOT");
        _particleRootGO.transform.SetParent(transform);
    }

    #region 主要播放方法

    /// <summary>
    /// 播放粒子效果
    /// </summary>
    /// <param name="effectName">效果名称</param>
    /// <param name="position">生成位置</param>
    /// <param name="rotation">生成旋转</param>
    /// <param name="parent">父节点</param>
    /// <param name="autoDestroy">是否自动销毁</param>
    /// <param name="destroyDelay">销毁延迟时间</param>
    /// <param name="scale">缩放比例</param>
    public ParticleSystem PlayEffect(string effectName,
        Vector3 position,
        Quaternion rotation = default,
        Transform parent = null,
        bool autoDestroy = true,
        float destroyDelay = -1f,
        Vector3? scale = null)
    {
        // 查找配置数据中的粒子效果
        ParticleData effectData = particleDatas.particleDataList.Find(x => x.effectName == effectName);

        if (effectData == null)
        {
            Debug.LogWarning("未找到指定的粒子效果：" + effectName);
            return null;
        }

        // 创建粒子效果实例
        GameObject effectGO = new GameObject(effectName);
        effectGO.transform.SetParent(parent != null ? parent : _particleRootGO.transform);
        effectGO.transform.position = position;
        effectGO.transform.rotation = rotation == default ? Quaternion.identity : rotation;

        if (scale.HasValue)
        {
            effectGO.transform.localScale = scale.Value;
        }

        GameObject prefab = Resources.Load<GameObject>(effectData.effectPath);
        if (prefab == null)
        {
            Debug.LogWarning($"粒子效果预制件加载失败：{effectData.effectPath}");
            Destroy(effectGO);
            return null;
        }

        GameObject instance = Instantiate(prefab, effectGO.transform);
        ParticleSystem particleSystem = instance.GetComponent<ParticleSystem>();
        if (particleSystem == null)
        {
            particleSystem = instance.AddComponent<ParticleSystem>();
        }

        ParticleInfo info = new ParticleInfo
        {
            effectName = effectName,
            particleSystem = particleSystem
        };

        particleSystem.Play();

        if (autoDestroy)
        {
            float delay = destroyDelay >= 0 ? destroyDelay : particleSystem.main.duration;
            info.autoDestroyCoroutine = StartCoroutine(AutoDestroyEffect(info, delay));
        }

        activeParticleEffects.Add(info);
        return particleSystem;
    }

    #endregion

    #region 效果管理

    /// <summary>
    /// 停止指定粒子效果
    /// </summary>
    /// <param name="effectName">效果名称</param>
    /// <param name="immediate">是否立即销毁</param>
    public void StopEffect(string effectName, bool immediate = false)
    {
        ParticleInfo info = activeParticleEffects.Find(x => x.effectName == effectName);
        if (info == null)
        {
            Debug.LogWarning("未找到活跃的粒子效果：" + effectName);
            return;
        }

        if (info.autoDestroyCoroutine != null)
        {
            StopCoroutine(info.autoDestroyCoroutine);
        }

        if (immediate)
        {
            Destroy(info.particleSystem.gameObject);
            activeParticleEffects.Remove(info);
        }
        else
        {
            info.particleSystem.Stop();
            StartCoroutine(AutoDestroyEffect(info, info.particleSystem.main.duration));
        }
    }

    #endregion

    #region 协程方法

    /// <summary>
    /// 自动销毁粒子效果
    /// </summary>
    private IEnumerator AutoDestroyEffect(ParticleInfo info, float delay)
    {
        yield return new WaitForSeconds(delay);

        if (info.particleSystem != null && info.particleSystem.transform.parent != null)
        {
            Destroy(info.particleSystem.transform.parent.gameObject);
        }

        activeParticleEffects.Remove(info);
    }

    #endregion
}