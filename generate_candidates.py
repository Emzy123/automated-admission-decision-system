import pandas as pd
import random
import string
from faker import Faker

# Initialize Faker with English (Nigeria) locale if possible, or just English
# Faker doesn't have a specific 'en_NG' for all providers, but we can simulate names.
fake = Faker()

# Define States and LGAs (Subset from research for simulation)
STATES_LGAS = {
    "Kogi": ["Adavi", "Ajaokuta", "Ankpa", "Bassa", "Dekina", "Ibaji", "Idah", "Igalamela-Odolu", "Ijumu", "Kabba/Bunu", "Kogi", "Lokoja", "Mopa-Muro", "Ofu", "Ogori/Magongo", "Okehi", "Okene", "Olamaboro", "Omala", "Yagba East", "Yagba West"],
    "Adamawa": ["Demsa", "Fufure", "Ganye", "Gayuk", "Gombi", "Grie", "Hong", "Jada", "Larmurde", "Madagali", "Maiha", "Mayo Belwa", "Michika", "Mubi North", "Mubi South", "Numan", "Shelleng", "Song", "Toungo", "Yola North", "Yola South"],
    "Bauchi": ["Alkaleri", "Bauchi", "Bogoro", "Damban", "Darazo", "Dass", "Gamawa", "Ganjuwa", "Giade", "Itas/Gadau", "Jama'are", "Katagum", "Kirfi", "Misau", "Ningi", "Shira", "Tafawa Balewa", "Toro", "Warji", "Zaki"],
    "Bayelsa": ["Brass", "Ekeremor", "Kolokuma/Opokuma", "Nembe", "Ogbia", "Sagbama", "Southern Ijaw", "Yenagoa"],
    "Benue": ["Agatu", "Apa", "Ado", "Buruku", "Gboko", "Guma", "Gwer East", "Gwer West", "Katsina-Ala", "Konshisha", "Kwande", "Logo", "Makurdi", "Obi", "Ogbadibo", "Ohimini", "Oju", "Okpokwu", "Oturkpo", "Tarka", "Ukum", "Ushongo", "Vandeikya"],
    "Borno": ["Abadam", "Askira/Uba", "Bama", "Bayo", "Biu", "Chibok", "Damboa", "Dikwa", "Guzamala", "Gubio", "Hawul", "Gwoza", "Jere", "Kaga", "Kala/Balge", "Konduga", "Kukawa", "Kwaya Kusar", "Mafa", "Magumeri", "Maiduguri", "Mobbar", "Marte", "Monguno", "Ngala", "Nganzai", "Shani"],
    "Jigawa": ["Auyo", "Babura", "Buji", "Biriniwa", "Birnin Kudu", "Dutse", "Gagarawa", "Garki", "Gumel", "Guri", "Gwaram", "Gwiwa", "Hadejia", "Jahun", "Kafin Hausa", "Kazaure", "Kiri Kasama", "Kiyawa", "Kaugama", "Maigatari", "Malam Madori", "Miga", "Sule Tankarkar", "Roni", "Ringim", "Yankwashi", "Taura"],
    "Kaduna": ["Birnin Gwari", "Chikun", "Giwa", "Ikara", "Igabi", "Jaba", "Jema'a", "Kachia", "Kaduna North", "Kaduna South", "Kagarko", "Kajuru", "Kaura", "Kauru", "Kubau", "Kudan", "Lere", "Makarfi", "Sabon Gari", "Sanga", "Soba", "Zangon Kataf", "Zaria"],
    "Kano": ["Ajingi", "Albasu", "Bagwai", "Bebeji", "Bichi", "Bunkure", "Dala", "Dambatta", "Dawakin Kudu", "Dawakin Tofa", "Doguwa", "Fagge", "Gabasawa", "Garko", "Garun Mallam", "Gaya", "Gezawa", "Gwale", "Gwarzo", "Kabo", "Kano Municipal", "Karaye", "Kibiya", "Kiru", "Kumbotso", "Kunchi", "Kura", "Madobi", "Makoda", "Minjibir", "Nasarawa", "Rano", "Rimin Gado", "Rogo", "Shanono", "Sumaila", "Takai", "Tarauni", "Tofa", "Tsanyawa", "Tudun Wada", "Ungogo", "Warawa", "Wudil"],
    "Katsina": ["Bakori", "Batagarawa", "Batsari", "Baure", "Bindawa", "Charanchi", "Dandume", "Danja", "Dan Musa", "Daura", "Dutsi", "Dutsin Ma", "Faskari", "Funtua", "Ingawa", "Jibia", "Kafur", "Kaita", "Kankara", "Kankia", "Katsina", "Kurfi", "Kusada", "Mai'Adua", "Malumfashi", "Mani", "Mashi", "Musawa", "Rimi", "Sabuwa", "Safana", "Sandamu", "Zango"],
    "Kebbi": ["Aleiro", "Arewa Dandi", "Argungu", "Augie", "Bagudo", "Birnin Kebbi", "Bunza", "Dandi", "Fakai", "Gwandu", "Jega", "Kalgo", "Koko/Besse", "Maiyama", "Ngaski", "Sakaba", "Shanga", "Suru", "Wasagu/Danko", "Yauri", "Zuru"],
    "Nasarawa": ["Akwanga", "Awe", "Doma", "Karu", "Keana", "Keffi", "Kokona", "Lafia", "Nasarawa", "Nasarawa Egon", "Obi", "Toto", "Wamba"],
    "Niger": ["Agaie", "Agwara", "Bida", "Borgu", "Bosso", "Chanchaga", "Edati", "Gbako", "Gurara", "Katcha", "Kontagora", "Lapai", "Lavun", "Magama", "Mariga", "Mashegu", "Mokwa", "Muya", "Paikoro", "Rafi", "Rijau", "Shiroro", "Suleja", "Tafa", "Wushishi"],
    "Plateau": ["Barkin Ladi", "Bassa", "Bokkos", "Jos East", "Jos North", "Jos South", "Kanam", "Kanke", "Langtang North", "Langtang South", "Mangu", "Mikang", "Pankshin", "Qua'an Pan", "Riyom", "Shendam", "Wase"],
    "Rivers": ["Abua/Odual", "Ahoada East", "Ahoada West", "Akuku-Toru", "Andoni", "Asari-Toru", "Bonny", "Degema", "Eleme", "Emuoha", "Etche", "Gokana", "Ikwerre", "Khana", "Obio/Akpor", "Ogba/Egbema/Ndoni", "Ogu/Bolo", "Okrika", "Omuma", "Opobo/Nkoro", "Oyigbo", "Port Harcourt", "Tai"],
    "Sokoto": ["Binji", "Bodinga", "Dange Shuni", "Gada", "Goronyo", "Gudu", "Gwadabawa", "Illela", "Isa", "Kebbe", "Kware", "Rabah", "Sabon Birni", "Shagari", "Silame", "Sokoto North", "Sokoto South", "Tambuwal", "Tangaza", "Tureta", "Wamako", "Wurno", "Yabo"],
    "Taraba": ["Ardo Kola", "Bali", "Donga", "Gashaka", "Gassol", "Ibi", "Jalingo", "Karim Lamido", "Kumi", "Lau", "Sardauna", "Takum", "Ussa", "Wukari", "Yorro", "Zing"],
    "Yobe": ["Bade", "Bursari", "Damaturu", "Fika", "Fune", "Geidam", "Gujba", "Gulani", "Jakusko", "Karasuwa", "Machina", "Nangere", "Nguru", "Potiskum", "Tarmuwa", "Yunusari", "Yusufari"],
    "Zamfara": ["Anka", "Bakura", "Birnin Magaji/Kiyaw", "Bukkuyum", "Bungudu", "Gummi", "Gusau", "Kaura Namoda", "Maradun", "Maru", "Shinkafi", "Talata Mafara", "Chafe", "Zurmi"],
    "Lagos": ["Agege", "Ajeromi-Ifelodun", "Alimosho", "Amuwo-Odofin", "Apapa", "Badagry", "Epe", "Eti Osa", "Ibeju-Lekki", "Ifako-Ijaiye", "Ikeja", "Ikorodu", "Kosofe", "Lagos Island", "Lagos Mainland", "Mushin", "Ojo", "Oshodi-Isolo", "Shomolu", "Surulere"],
    "Oyo": ["Afijio", "Akinyele", "Atiba", "Atisbo", "Egbeda", "Ibadan North", "Ibadan North-East", "Ibadan North-West", "Ibadan South-East", "Ibarapa Central", "Ibadan South-West", "Ibarapa East", "Ido", "Ibarapa North", "Irepo", "Iseyin", "Itesiwaju", "Iwajowa", "Kajola", "Lagelu", "Ogbomosho North", "Ogbomosho South", "Ogo Oluwa", "Olorunsogo", "Oluyole", "Ona Ara", "Orelope", "Ori Ire", "Oyo", "Oyo East", "Saki East", "Saki West", "Surulere Oyo State"],
    "Ogun": ["Abeokuta North", "Abeokuta South", "Ado-Odo/Ota", "Egbado North", "Ewekoro", "Egbado South", "Ijebu North", "Ijebu East", "Ifo", "Ijebu Ode", "Ijebu North East", "Imeko Afon", "Ikenne", "Ipokia", "Odeda", "Obafemi Owode", "Odogbolu", "Remo North", "Ogun Waterside", "Shagamu"],
    "Ondo": ["Akoko North-East", "Akoko North-West", "Akoko South-West", "Akoko South-East", "Akure North", "Akure South", "Ese Odo", "Idanre", "Ifedore", "Ilaje", "Irele", "Ile Oluji/Okeigbo", "Odigbo", "Okitipupa", "Ondo West", "Ose", "Ondo East", "Owo"],
    "Osun": ["Atakunmosa East", "Atakunmosa West", "Aiyedaade", "Aiyedire", "Boluwaduro", "Boripe", "Ede North", "Ede South", "Ife Central", "Ife East", "Ife North", "Ife South", "Egbedore", "Ejigbo", "Ifedayo", "Ifelodun", "Ila", "Ilesa North", "Ilesa South", "Irepodun", "Irewole", "Isokan", "Iwo", "Obokun", "Odo Otin", "Ola Oluwa", "Olorunda", "Oriade", "Orolu", "Osogbo"],
    "Edo": ["Akoko-Edo", "Egor", "Esan Central", "Esan North-East", "Esan South-East", "Esan West", "Etsako Central", "Etsako East", "Etsako West", "Igueben", "Ikpoba Okha", "Orhionmwon", "Oredo", "Ovia North-East", "Ovia South-West", "Owan East", "Owan West", "Uhunmwonde"],
    "Delta": ["Aniocha North", "Aniocha South", "Bomadi", "Burutu", "Ethiope West", "Ethiope East", "Ika North East", "Ika South", "Isoko North", "Isoko South", "Ndokwa East", "Ndokwa West", "Okpe", "Oshimili North", "Oshimili South", "Patani", "Sapele", "Udu", "Ughelli North", "Ukwuani", "Ughelli South", "Uvwie", "Warri North", "Warri South", "Warri South West"],
    "Enugu": ["Awgu", "Aninri", "Enugu East", "Enugu North", "Ezeagu", "Enugu South", "Igbo Etiti", "Igbo Eze North", "Igbo Eze South", "Isi Uzo", "Nkanu East", "Nkanu West", "Nsukka", "Udenu", "Oji River", "Uzo Uwani", "Udi"],
    "Anambra": ["Aguata", "Anambra East", "Anaocha", "Awka North", "Anambra West", "Awka South", "Ayamelum", "Dunukofia", "Ekwusigo", "Idemili North", "Idemili South", "Ihiala", "Njikoka", "Nnewi North", "Nnewi South", "Ogbaru", "Onitsha North", "Onitsha South", "Orumba North", "Orumba South", "Oyi"],
    "Imo": ["Aboh Mbaise", "Ahiazu Mbaise", "Ehime Mbano", "Ezinihitte", "Ideato North", "Ideato South", "Ihitte/Uboma", "Ikeduru", "Isiala Mbano", "Mbaitoli", "Isu", "Ngor Okpala", "Njaba", "Nkwerre", "Nwangele", "Obowo", "Oguta", "Ohaji/Egbema", "Okigwe", "Orlu", "Orsu", "Oru East", "Oru West", "Owerri Municipal", "Owerri North", "Unuimo", "Owerri West"],
    "Abia": ["Aba North", "Aba South", "Arochukwu", "Bende", "Ikwuano", "Isiala Ngwa North", "Isiala Ngwa South", "Isuikwuato", "Obingwa", "Ohafia", "Osisioma", "Ugwunagbo", "Ukwa East", "Ukwa West", "Umuahia North", "Umuahia South", "Umu Nneochi"],
    "Akwa Ibom": ["Abak", "Eastern Obolo", "Eket", "Esit Eket", "Essien Udim", "Etim Ekpo", "Etinan", "Ibeno", "Ibesikpo Asutan", "Ibiono-Ibom", "Ikot Abasi", "Ika", "Ikono", "Ikot Ekpene", "Ini", "Mkpat-Enin", "Itu", "Mbo", "Nsit-Atai", "Nsit-Ibom", "Nsit-Ubium", "Obot Akara", "Okobo", "Onna", "Oron", "Udung-Uko", "Ukanafun", "Oruk Anam", "Uruan", "Urue-Offong/Oruko", "Uyo"]
}

# Grouping for distribution
CATCHMENT = ["Kogi"]
ELDS = ["Adamawa", "Bauchi", "Bayelsa", "Benue", "Borno", "Jigawa", "Kaduna", "Kano", "Katsina", "Kebbi", "Nasarawa", "Niger", "Plateau", "Rivers", "Sokoto", "Taraba", "Yobe", "Zamfara"]
OTHERS = [s for s in STATES_LGAS.keys() if s not in CATCHMENT and s not in ELDS]

# CUSTECH Courses
COURSES = {
    "FCI": ["Computer Science", "Software Engineering", "Cyber Security", "Information Technology"],
    "Engineering": ["Computer Engineering", "Mechanical Engineering", "Civil and Mining Engineering", "Electrical Engineering", "Chemical Engineering"],
    "Science": ["Biochemistry", "Microbiology", "Physics", "Chemistry", "Mathematics"]
}
ALL_COURSES = COURSES["FCI"] + COURSES["Engineering"] + COURSES["Science"]

# Realistic Nigerian Names Simulation
# Since Faker doesn't have a robust Nigeria locale, we'll use a mix of common prefixes/suffixes or predefined lists.
FIRST_NAMES = ["Musa", "Chinedu", "Bola", "Yusuf", "Okeke", "Tinubu", "Adebayo", "Emeka", "Amina", "Ngozi", "Ibrahim", "Tunde", "Zainab", "Olawale", "Chinonso", "Fatima", "Segun", "Uche", "Abubakar", "Funke"]
LAST_NAMES = ["Yusuf", "Okeke", "Tinubu", "Akinyemi", "Obi", "Danjuma", "Okonkwo", "Balogun", "Sani", "Eze", "Bello", "Ojo", "Nwosu", "Adamu", "Olatunji", "Umar", "Ibe", "Gbadamosi", "Okafor", "Usman"]

def generate_fullname():
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}".upper()

def generate_jamb_reg():
    return "2025" + "".join(random.choices(string.digits, k=6))

def generate_waec_no():
    return "".join(random.choices(string.digits, k=10))

def get_state_and_lga():
    r = random.random()
    if r < 0.20:
        state = random.choice(CATCHMENT)
    elif r < 0.50:
        state = random.choice(ELDS)
    else:
        state = random.choice(OTHERS)
    lga = random.choice(STATES_LGAS[state])
    return state, lga

def generate_utme_scores():
    r = random.random()
    if r < 0.10:
        total = random.randint(280, 360)
    elif r < 0.60:
        total = random.randint(180, 279)
    elif r < 0.80:
        total = random.randint(140, 179)
    else:
        total = random.randint(80, 139)
    
    # Split total into 4 subjects (Eng + 3 others)
    # Use a simpler proportion-based approach to ensure valid ranges
    # Standard JAMB subjects are 100 marks each
    parts = [random.uniform(0.5, 1.0) for _ in range(4)]
    sum_parts = sum(parts)
    scores = [int((p / sum_parts) * total) for p in parts]
    
    # Adjust for rounding errors to ensure exact sum
    diff = total - sum(scores)
    for i in range(abs(diff)):
        scores[i % 4] += 1 if diff > 0 else -1
        
    eng, math, phy, chem = scores
    return total, eng, math, phy, chem

def generate_waec_grades():
    grades = ["A1", "B2", "B3", "C4", "C5", "C6", "D7", "E8", "F9"]
    pass_grades = ["A1", "B2", "B3", "C4", "C5", "C6"]
    fail_grades = ["D7", "E8", "F9"]
    
    r = random.random()
    res = []
    if r < 0.75: # Pass all 5
        res = [random.choice(pass_grades) for _ in range(5)]
    elif r < 0.90: # Fail Eng or Math
        res = [random.choice(pass_grades) for _ in range(5)]
        idx = random.choice([0, 1]) # G1 or G2
        res[idx] = random.choice(fail_grades)
    else: # Fail science
        res = [random.choice(pass_grades) for _ in range(5)]
        idx = random.choice([2, 3]) # G3 or G4
        res[idx] = random.choice(fail_grades)
    return res

data = []
jamb_regs = set()
waec_nos = set()

for _ in range(1000):
    # Unique IDs
    jr = generate_jamb_reg()
    while jr in jamb_regs: jr = generate_jamb_reg()
    jamb_regs.add(jr)
    
    wn = generate_waec_no()
    while wn in waec_nos: wn = generate_waec_no()
    waec_nos.add(wn)
    
    state, lga = get_state_and_lga()
    total, eng, math, phy, chem = generate_utme_scores()
    waec_res = generate_waec_grades()
    
    row = {
        "JAMB_REG": jr,
        "FULLNAME": generate_fullname(),
        "STATE": state,
        "LGA": lga,
        "UTME_SCORE": total,
        "UTME_ENG": eng,
        "UTME_MATH": math,
        "UTME_PHY": phy,
        "UTME_CHEM": chem,
        "FIRST_CHOICE": "Confluence University of Science and Technology",
        "FIRST_COURSE": random.choice(ALL_COURSES),
        "WAEC_NO": wn,
        "WAEC_YEAR": random.choice([2023, 2024]),
        "G1_SUBJECT": "English Language",
        "G1_GRADE": waec_res[0],
        "G2_SUBJECT": "Mathematics",
        "G2_GRADE": waec_res[1],
        "G3_SUBJECT": "Physics",
        "G3_GRADE": waec_res[2],
        "G4_SUBJECT": "Chemistry",
        "G4_GRADE": waec_res[3],
        "G5_SUBJECT": random.choice(["Biology", "Agricultural Science", "Geography"]),
        "G5_GRADE": waec_res[4]
    }
    data.append(row)

df = pd.DataFrame(data)
df.to_csv("test_candidates_1000.csv", index=False)
print("CSV generated successfully: test_candidates_1000.csv")
