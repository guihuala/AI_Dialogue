/// <summary>
/// 普通类型的单例类(不继承mono)
/// </summary>
/// <typeparam name="T"></typeparam>
public class SingletonNoMono<T> where T : class, new()
{
    protected static T instance = new T();

    public static T Instance
    {
        get
        {
            if (instance == null)
                instance = new T();
            return instance;
        }
    }
}

