"""Константы для интеграции Advanced BIA Scale."""

from homeassistant.const import UnitOfMass, PERCENTAGE, UnitOfLength, CONF_UNIT_OF_MEASUREMENT

DOMAIN = "adv_bia_scale"

# BLE Manufacturer ID для OKOK/Scale
MANUFACTURER_ID_OKOK = 8394

# Типы сенсоров
SENSOR_WEIGHT = "weight"
SENSOR_IMPEDANCE = "impedance"
SENSOR_BMI = "bmi"
SENSOR_BODY_FAT = "body_fat"
SENSOR_MUSCLE_MASS = "muscle_mass"
SENSOR_WATER = "water"
SENSOR_BONE_MASS = "bone_mass"
SENSOR_VISCERAL_FAT = "visceral_fat"
SENSOR_BMR = "bmr"
SENSOR_METABOLIC_AGE = "metabolic_age"
SENSOR_BODY_TYPE = "body_type"
SENSOR_PROTEIN = "protein"
SENSOR_FAT_FREE_MASS = "fat_free_mass"
SENSOR_SUBCUTANEOUS_FAT = "subcutaneous_fat"
SENSOR_HEART_RATE = "heart_rate"

SENSOR_TYPES = {
    SENSOR_WEIGHT: {
        "name": "Вес",
        "unit": UnitOfMass.KILOGRAMS,
        "device_class": "weight",
        "icon": "mdi:scale",
        "state_class": "measurement",
    },
    SENSOR_IMPEDANCE: {
        "name": "Импеданс",
        "unit": "Ом",
        "device_class": None,
        "icon": "mdi:omega",
        "state_class": "measurement",
    },
    SENSOR_BMI: {
        "name": "ИМТ (BMI)",
        "unit": "кг/м²",
        "device_class": None,
        "icon": "mdi:human-male-height-variant",
        "state_class": "measurement",
    },
    SENSOR_BODY_FAT: {
        "name": "Жировая масса",
        "unit": PERCENTAGE,
        "device_class": None,
        "icon": "mdi:percent",
        "state_class": "measurement",
    },
    SENSOR_MUSCLE_MASS: {
        "name": "Мышечная масса",
        "unit": UnitOfMass.KILOGRAMS,
        "device_class": "weight",
        "icon": "mdi:arm-flex",
        "state_class": "measurement",
    },
    SENSOR_WATER: {
        "name": "Вода",
        "unit": PERCENTAGE,
        "device_class": None,
        "icon": "mdi:water-percent",
        "state_class": "measurement",
    },
    SENSOR_BONE_MASS: {
        "name": "Масса костей",
        "unit": UnitOfMass.KILOGRAMS,
        "device_class": "weight",
        "icon": "mdi:bone",
        "state_class": "measurement",
    },
    SENSOR_VISCERAL_FAT: {
        "name": "Висцеральный жир",
        "unit": None,
        "device_class": None,
        "icon": "mdi:stomach",
        "state_class": "measurement",
    },
    SENSOR_BMR: {
        "name": "Базовый обмен (BMR)",
        "unit": "ккал/день",
        "device_class": None,
        "icon": "mdi:fire",
        "state_class": "measurement",
    },
    SENSOR_METABOLIC_AGE: {
        "name": "Метаболический возраст",
        "unit": "лет",
        "device_class": None,
        "icon": "mdi:cake-variant",
        "state_class": "measurement",
    },
    SENSOR_BODY_TYPE: {
        "name": "Тип тела",
        "unit": None,
        "device_class": None,
        "icon": "mdi:human",
        "state_class": None,
    },
    SENSOR_PROTEIN: {
        "name": "Протеины",
        "unit": PERCENTAGE,
        "device_class": None,
        "icon": "mdi:food-steak",
        "state_class": "measurement",
    },
    SENSOR_FAT_FREE_MASS: {
        "name": "Масса без жира",
        "unit": UnitOfMass.KILOGRAMS,
        "device_class": "weight",
        "icon": "mdi:weight-lifter",
        "state_class": "measurement",
    },
    SENSOR_SUBCUTANEOUS_FAT: {
        "name": "Подкожный жир",
        "unit": PERCENTAGE,
        "device_class": None,
        "icon": "mdi:percent-box",
        "state_class": "measurement",
    },
    SENSOR_HEART_RATE: {
        "name": "Пульс",
        "unit": "уд/мин",
        "device_class": None,
        "icon": "mdi:heart-pulse",
        "state_class": "measurement",
    },
}

# Ключи конфигурации
CONF_HEIGHT = "height"
CONF_BIRTH_DATE = "birth_date"
CONF_GENDER = "gender"
CONF_ACTIVITY_LEVEL = "activity_level"
CONF_SCALE_MAC = "scale_mac"

GENDER_MALE = "male"
GENDER_FEMALE = "female"

# Уровни активности
ACTIVITY_SEDENTARY = "sedentary"
ACTIVITY_LIGHT = "light"
ACTIVITY_MODERATE = "moderate"
ACTIVITY_ACTIVE = "active"
ACTIVITY_VERY_ACTIVE = "very_active"

ACTIVITY_MULTIPLIERS = {
    ACTIVITY_SEDENTARY: 1.2,
    ACTIVITY_LIGHT: 1.375,
    ACTIVITY_MODERATE: 1.55,
    ACTIVITY_ACTIVE: 1.725,
    ACTIVITY_VERY_ACTIVE: 1.9,
}

ACTIVITY_LABELS = {
    ACTIVITY_SEDENTARY: "Сидячий (1.2)",
    ACTIVITY_LIGHT: "Малая активность (1.375)",
    ACTIVITY_MODERATE: "Умеренная активность (1.55)",
    ACTIVITY_ACTIVE: "Активный (1.725)",
    ACTIVITY_VERY_ACTIVE: "Очень активный (1.9)",
}

GENDER_LABELS = {
    GENDER_MALE: "Мужской",
    GENDER_FEMALE: "Женский",
}

BODY_TYPE_LABELS = {
    "underweight": "Недостаточный вес",
    "normal": "Норма",
    "athletic": "Атлетичный",
    "overweight": "Избыточный вес",
    "obese": "Ожирение",
}


def get_activity_label(key):
    """Вернуть русское название активности."""
    return ACTIVITY_LABELS.get(key, key)


def get_gender_label(key):
    """Вернуть русское название пола."""
    return GENDER_LABELS.get(key, key)


def get_body_type_label(key):
    """Вернуть русское название типа тела."""
    return BODY_TYPE_LABELS.get(key, key)


def calculate_bmi(weight_kg, height_cm):
    """Вычислить ИМТ."""
    height_m = height_cm / 100.0
    return round(weight_kg / (height_m * height_m), 1)


def calculate_body_fat(weight_kg, impedance, age, gender, height_cm):
    """Вычислить % жира по BIA."""
    bmi = calculate_bmi(weight_kg, height_cm)
    if gender == GENDER_MALE:
        body_fat = 1.20 * bmi + 0.23 * age - 16.2 - (0.0 if impedance == 0 else 0.0001 * impedance)
    else:
        body_fat = 1.20 * bmi + 0.23 * age - 5.4 - (0.0 if impedance == 0 else 0.0001 * impedance)
    body_fat = max(2.0, min(75.0, body_fat))
    return round(body_fat, 1)


def calculate_muscle_mass(weight_kg, body_fat_percent):
    """Вычислить мышечную массу."""
    lean_mass = weight_kg * (1 - body_fat_percent / 100)
    muscle = lean_mass * 0.52
    return round(muscle, 2)


def calculate_water(weight_kg, body_fat_percent, gender):
    """Вычислить % воды."""
    tbw_percent = 50.0 + (0.5 if gender == GENDER_MALE else -0.5)
    water = tbw_percent * (1 - body_fat_percent / 100) * 1.1
    water = max(10.0, min(85.0, water))
    return round(water, 1)


def calculate_bone_mass(weight_kg, height_cm, gender):
    """Вычислить массу костей."""
    if gender == GENDER_MALE:
        bone = 0.0031 * height_cm**2 + 0.0024 * weight_kg - 0.0008 * 30
    else:
        bone = 0.0028 * height_cm**2 + 0.0022 * weight_kg - 0.0006 * 30
    bone = max(0.5, min(8.0, bone))
    return round(bone, 2)


def calculate_visceral_fat(bmi, age, gender, waist_cm=None):
    """Вычислить висцеральный жир."""
    vf = 1.0 + 0.1 * bmi + 0.05 * age
    if gender == GENDER_MALE:
        vf += 1.5
    if waist_cm:
        vf += 0.1 * (waist_cm - 80)
    vf = max(1.0, min(30.0, vf))
    return round(vf, 0)


def calculate_bmr(weight_kg, height_cm, age, gender):
    """Базовый обмен веществ (Mifflin-St Jeor)."""
    if gender == GENDER_MALE:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
    else:
        bmr = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161
    return round(bmr, 0)


def calculate_tdee(bmr, activity_level):
    """Общая энергия за день (TDEE)."""
    return round(bmr * ACTIVITY_MULTIPLIERS.get(activity_level, 1.2), 0)


def calculate_metabolic_age(weight_kg, height_cm, age, gender, body_fat_percent):
    """Метаболический возраст."""
    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    std_bmr = calculate_bmr(70 if gender == GENDER_MALE else 55, height_cm, age, gender)
    ratio = bmr / std_bmr if std_bmr > 0 else 1.0
    meta_age = age * (2.0 - ratio)
    meta_age = max(10.0, min(100.0, meta_age))
    return round(meta_age, 0)


def get_body_type(bmi, body_fat_percent, gender):
    """Тип тела."""
    if bmi < 18.5:
        return "underweight"
    elif bmi < 25:
        if body_fat_percent < (15 if gender == GENDER_MALE else 22):
            return "athletic"
        elif body_fat_percent < (20 if gender == GENDER_MALE else 28):
            return "normal"
        else:
            return "overweight"
    elif bmi < 30:
        return "overweight"
    else:
        return "obese"


def calculate_protein(weight_kg, body_fat_percent, muscle_mass):
    """Вычислить % протеинов."""
    lean_mass = weight_kg * (1 - body_fat_percent / 100)
    if lean_mass <= 0:
        return 0.0
    protein = (muscle_mass * 0.20 / lean_mass) * 100
    protein = max(5.0, min(30.0, protein))
    return round(protein, 1)


def calculate_subcutaneous_fat(body_fat_percent, visceral_fat):
    """Подкожный жир."""
    if body_fat_percent <= 0:
        return 0.0
    subcut = body_fat_percent - (visceral_fat * 0.8)
    subcut = max(0.0, min(50.0, subcut))
    return round(subcut, 1)


def calculate_fat_free_mass(weight_kg, body_fat_percent):
    """Масса без жира."""
    if weight_kg <= 0:
        return 0.0
    return round(weight_kg * (1 - body_fat_percent / 100), 2)


def calculate_age(birth_date):
    """Вычислить возраст из строки даты рождения (DD.MM.YYYY)."""
    from datetime import date, datetime
    try:
        dt = datetime.strptime(birth_date, "%d.%m.%Y").date()
    except (ValueError, TypeError):
        return 30
    today = date.today()
    age = today.year - dt.year
    if today.month < dt.month or (today.month == dt.month and today.day < dt.day):
        age -= 1
    return max(0, age)
