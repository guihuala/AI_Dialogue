using UnityEngine;

public class TimeManager : Singleton<TimeManager>
{
    // 当前时间倍率
    public float TimeFactor { get; private set; } = 1f;

    // 用于处理暂停、恢复等功能的状态
    public bool IsPaused { get; private set; }

    // 获取当前帧的时间（经过时间倍率调整）
    public float DeltaTime
    {
        get
        {
            // 如果暂停，返回0，否则按时间倍率调整
            return IsPaused ? 0f : Time.unscaledDeltaTime * TimeFactor;
        }
    }

    // 获取固定更新的时间（经过时间倍率调整）
    public float FixedDeltaTime
    {
        get
        {
            // 固定时间间隔也按时间倍率调整
            return IsPaused ? 0f : 0.02f * TimeFactor; // 0.02f 是默认的 fixedDeltaTime
        }
    }

    // 更新时间
    private void Update()
    {
        if (!IsPaused)
        {
            Time.timeScale = TimeFactor; 
        }
    }

    // 设置时间倍率
    public void SetTimeFactor(float factor)
    {
        TimeFactor = factor;
    }

    // 暂停时间
    public void PauseTime()
    {
        IsPaused = true;
    }

    // 恢复时间
    public void ResumeTime()
    {
        IsPaused = false;
    }
}