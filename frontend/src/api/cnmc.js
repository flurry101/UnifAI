// Common National Material Code (CNMC) Registry API
import { apiFetch } from './client';

export const SAMPLE_CNMC_CATALOG = [
  {
    id: "CNMC-REG-001",
    cnmc_code: "CNMC-3196-CYL-142",
    standardized_description: "CYLINDER LPG LOW CARBON STEEL DOMESTIC 14.2 KG CAPACITY FITTED SC VALVE AS PER IS:3196 (PART 1)",
    status: "APPROVED",
    created_at: "2026-03-15T10:00:00Z",
    core_attributes: {
      standard: "IS:3196 PART 1",
      commodity_group: "PRESSURE VESSELS",
      nominal_capacity: "14.2 KG",
      water_capacity: "33.3 L",
      test_pressure: "25 BAR",
      canonical_uom: "NOS"
    },
    linked_cpse_materials: [
      { cpse: "IOCL", material_code: "1236/1231", relation: "IDENTICAL" },
      { cpse: "BPCL", material_code: "BPCL-LPG-CYL-14.2", relation: "IDENTICAL" },
      { cpse: "HPCL", material_code: "HPCL-14.2-DOM-CYL", relation: "EQUIVALENT" }
    ]
  },
  {
    id: "CNMC-REG-002",
    cnmc_code: "CNMC-A106-PIPE-DN100",
    standardized_description: "PIPE CARBON STEEL SEAMLESS HIGH TEMPERATURE SERVICE ASTM A106 GRADE B NOMINAL SIZE DN 100 (4 INCH) SCH 40",
    status: "APPROVED",
    created_at: "2026-03-18T14:30:00Z",
    core_attributes: {
      standard: "ASTM A106 / ASME SA106",
      material_grade: "GRADE B",
      nominal_size: "DN 100 / 4 INCH",
      wall_thickness: "SCH 40 (6.02 MM)",
      canonical_uom: "MTR"
    },
    linked_cpse_materials: [
      { cpse: "IOCL", material_code: "IOCL_PIPE_DN100_CS", relation: "EQUIVALENT" },
      { cpse: "ONGC", material_code: "ONGC_PIPE_4IN_CS_A106", relation: "IDENTICAL" },
      { cpse: "GAIL", material_code: "GAIL-CS-P-04-A106", relation: "IDENTICAL" }
    ]
  },
  {
    id: "CNMC-REG-003",
    cnmc_code: "CNMC-A216-VLV-BALL-06",
    standardized_description: "VALVE BALL TRUNNION MOUNTED FULL BORE 6 INCH CLASS 300 FLANGED RF BODY ASTM A216 WCB FIRE SAFE API 6D / 607",
    status: "PROPOSED",
    created_at: "2026-04-01T09:15:00Z",
    core_attributes: {
      standard: "API 6D",
      pressure_class: "ASME CLASS 300",
      size: "6 INCH (DN 150)",
      body_material: "ASTM A216 WCB",
      trim: "13CR / SS316",
      canonical_uom: "NOS"
    },
    linked_cpse_materials: [
      { cpse: "GAIL", material_code: "GAIL_VALVE_BALL_150_CL300", relation: "IDENTICAL" },
      { cpse: "HPCL", material_code: "HPCL_VLV_BL_06_300", relation: "EQUIVALENT" }
    ]
  }
];

export async function fetchCnmcCatalog() {
  try {
    const list = await apiFetch('/api/v1/cnmc/');
     return list;
  } catch (err) {
     throw err;
  }
}

export async function fetchCnmcDetail(cnmcId) {
  try {
    return await apiFetch(`/api/v1/cnmc/${encodeURIComponent(cnmcId)}`);
  } catch (err) {
    const found = SAMPLE_CNMC_CATALOG.find(c => c.id === cnmcId || c.cnmc_code === cnmcId);
    if (found) return found;
    throw err;
  }
}

