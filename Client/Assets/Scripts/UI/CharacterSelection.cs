using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using UnityEngine.UI;

public class CharacterSelection : MonoBehaviour
{
    [System.Serializable]
    public class Candidate
    {
        public string id;
        public string name;
        public string description;
        public Stats stats;
    }

    [System.Serializable]
    public class Stats
    {
        public float money;
        public float sanity;
        public float gpa;
    }

    [System.Serializable]
    public class CandidateList
    {
        public List<Candidate> candidates;
    }

    [SerializeField] private string apiUrl = "http://localhost:8000/candidates";
    [SerializeField] private Transform container;
    [SerializeField] private GameObject candidatePrefab; // Should have Text components for Name/Desc
    [SerializeField] private Button startButton;

    private List<string> selectedIds = new List<string>();

    void Start()
    {
        StartCoroutine(FetchCandidates());
        startButton.onClick.AddListener(OnStartGame);
        startButton.interactable = false;
    }

    IEnumerator FetchCandidates()
    {
        using (UnityWebRequest webRequest = UnityWebRequest.Get(apiUrl))
        {
            yield return webRequest.SendWebRequest();

            if (webRequest.result == UnityWebRequest.Result.ConnectionError || webRequest.result == UnityWebRequest.Result.ProtocolError)
            {
                Debug.LogError("Error: " + webRequest.error);
            }
            else
            {
                var json = webRequest.downloadHandler.text;
                var list = JsonConvert.DeserializeObject<CandidateList>(json);
                PopulateUI(list.candidates);
            }
        }
    }

    void PopulateUI(List<Candidate> candidates)
    {
        foreach (var c in candidates)
        {
            GameObject go = Instantiate(candidatePrefab, container);
            // Assuming prefab has a script 'CandidateItem' or we just find child texts
            // For simplicity, let's assume we just set text if available
            var texts = go.GetComponentsInChildren<Text>();
            if (texts.Length > 0) texts[0].text = c.name;
            if (texts.Length > 1) texts[1].text = c.description;

            var btn = go.GetComponent<Button>();
            btn.onClick.AddListener(() => ToggleSelection(c.id, btn));
        }
    }

    void ToggleSelection(string id, Button btn)
    {
        if (selectedIds.Contains(id))
        {
            selectedIds.Remove(id);
            btn.image.color = Color.white;
        }
        else
        {
            if (selectedIds.Count < 3)
            {
                selectedIds.Add(id);
                btn.image.color = Color.green;
            }
        }

        startButton.interactable = selectedIds.Count == 3;
    }

    void OnStartGame()
    {
        // Pass selectedIds to GameDirector or save to PlayerPrefs
        string joined = string.Join(",", selectedIds);
        PlayerPrefs.SetString("SelectedRoommates", joined);
        UnityEngine.SceneManagement.SceneManager.LoadScene("GameScene");
    }
}
