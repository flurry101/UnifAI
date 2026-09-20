// Materials and Matching Pipeline API
import { apiFetch } from './client';

// Real CPSE Material examples from public benchmarks for rapid testing
export const SAMPLE_MATERIALS = [
  {
    material_id: "MAT-IOCL-CYL-14KG",
    cpse_id: "IOCL",
    original_material_code: "1236/1231",
    normalized_description: "14.2 KG CYLINDER DOMESTIC LPG NEW REPLACEMENT IS:3196 PART 1",
    source_system: "SAP_ECC",
    commodity_class: "CONTAINERS & PRESSURE VESSELS",
    specifications: {
      standard: "IS 3196 PART 1",
      water_capacity: "33.3 LITERS",
      test_pressure: "25 BAR",
      nominal_weight: "14.2 KG"
    }
  },
  {
    material_id: "MAT-ONGC-VLV-BALL-6IN",
    cpse_id: "ONGC",
    original_material_code: "VAL-BALL-06-600-CS",
    normalized_description: "VALVE BALL 6 INCH 600# FLANGED RF WCB BODY TRIM 13CR NACE MR0175 API 6D",
    source_system: "MAXIMO",
    commodity_class: "PIPING VALVES",
    specifications: {
      standard: "API 6D",
      size: "6 INCH (DN 150)",
      pressure_class: "ASME 600#",
      material_grade: "ASTM A216 WCB"
    }
  },
  {
    material_id: "MAT-GAIL-PIPE-12IN-X65",
    cpse_id: "GAIL",
    original_material_code: "PIPE-SAWL-12-SCH40",
    normalized_description: "PIPE CS 12 INCH SCH 40 API 5L GRADE X65 PSL2 SAW SEAMLESS EQUIVALENT",
    source_system: "ORACLE_EBS",
    commodity_class: "LINE PIPES",
    specifications: {
      standard: "API 5L PSL2",
      nominal_size: "12 INCH",
      grade: "API 5L X65",
      schedule: "SCH 40"
    }
  },
  {
    material_id: "MAT-NTPC-BLR-TUBES-T22",
    cpse_id: "NTPC",
    original_material_code: "BLR-TB-50.8-T22",
    normalized_description: "TUBE BOILER SEAMLESS ALLOY STEEL OD 50.8MM THK 5.6MM SA213 T22",
    source_system: "SAP_S4",
    commodity_class: "BOILER PRESSURE PARTS",
    specifications: {
      standard: "ASME SA213",
      grade: "GRADE T22 (2.25CR-1MO)",
      outer_diameter: "50.8 MM",
      wall_thickness: "5.6 MM"
    }
  }
];

export async function searchMaterials(query, limit = 10) {
  try {
    const data = await apiFetch(`/api/v1/materials?search=${encodeURIComponent(query)}&limit=${limit}`);
    return data;
  } catch (err) {
    return [];
  }
}

export async function fetchMaterialById(materialId) {
  try {
    const data = await apiFetch(`/api/v1/materials/${encodeURIComponent(materialId)}`);
    return data;
  } catch (err) {
    // If backend returns 404 or fails, check sample benchmark list
    const foundSample = SAMPLE_MATERIALS.find(m => m.material_id === materialId || m.original_material_code === materialId);
    if (foundSample) {
      return { ...foundSample, _isBenchmarkDemo: true };
    }
    throw err;
  }
}

export async function triggerAiMatch(materialId) {
  try {
    const proposals = await apiFetch(`/api/v1/materials/${encodeURIComponent(materialId)}/matches`, {
      method: 'POST',
    });
    return proposals;
  } catch (err) {
      throw err;
  }
}

export async function fetchExistingMatches(materialId) {
  try {
    return await apiFetch(`/api/v1/materials/${encodeURIComponent(materialId)}/matches`);
  } catch (err) {
    return [];
  }
}

