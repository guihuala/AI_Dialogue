using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;


[CreateAssetMenu(fileName = "New ParticleDataListSO", menuName = "CustomizedSO/ParticleDataListSO")]
public class ParticleDatas : ScriptableObject
{
    public List<ParticleData> particleDataList;
}