using System.Collections.Generic;
using UnityEngine;
using Newtonsoft.Json;

namespace SaveSystem
{
    [System.Serializable]
    public class SaveModel
    {
        // Public Properties (PascalCase)
        public string CurrentSessionId { get; private set; }
        public SaveData CurrentData { get; private set; }

        // Nested Class (PascalCase)
        [System.Serializable]
        public class SaveData
        {
            // Fields serialization friendly (camelCase for JSON compatibility if needed, but standard C# usually uses Pascal for public fields. 
            // However, NewtonSoft default is to keep case. Let's use lowerCamelCase for fields to match previous JSON structure or PascalCase with JsonProperty)
            // To be safe and clean, let's use PascalCase for C# and rely on default serialization or attributes if needed.
            // But previous code used lowercase in JSON. Let's stick to simple fields for now, maybe Attributes for JSON.
            
            [JsonProperty("money")]
            public float Money;
            
            [JsonProperty("sanity")]
            public float Sanity;
            
            [JsonProperty("gpa")]
            public float GPA;
            
            [JsonProperty("day")]
            public int Day;
            
            [JsonProperty("timeIndex")]
            public int TimeIndex;
            
            [JsonProperty("history")]
            public List<ChatMessage> History;
        }

        // Methods (PascalCase)
        public void SetSessionId(string id)
        {
            CurrentSessionId = id;
        }

        public string ToJson()
        {
            if (CurrentData == null) return "{}";
            return JsonConvert.SerializeObject(CurrentData);
        }

        public void FromJson(string json)
        {
            try 
            {
                CurrentData = JsonConvert.DeserializeObject<SaveData>(json);
            }
            catch
            {
                Debug.LogError("[SaveModel] Failed to parse JSON.");
                CurrentData = null;
            }
        }

        public void UpdateData(float money, float sanity, float gpa, int day, int timeIndex, List<ChatMessage> history)
        {
            CurrentData = new SaveData
            {
                Money = money,
                Sanity = sanity,
                GPA = gpa,
                Day = day,
                TimeIndex = timeIndex,
                History = history
            };
        }
    }
}
