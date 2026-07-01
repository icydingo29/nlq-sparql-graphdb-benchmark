from owlready2 import *

# Ontology initialization
onto = get_ontology("http://example.org/geo_ontology_final.owl")

with onto:
    # Classes #32
    class Place(Thing): pass
    class Continent(Thing): pass
    class Country(Thing): pass
    
    class Religion(Thing): pass
    class Form_of_Government(Thing): pass
    class Architecture(Thing): pass
    class Person(Thing): pass

    class PopulatedPlace(Place): pass
    class Village(PopulatedPlace): pass
    class City(PopulatedPlace): pass
    
    class Landmark(Place): pass
    class NaturalLandmark(Landmark): pass
    class CulturalLandmark(Landmark): pass
    class Building(CulturalLandmark): pass
    class Castle(Building): pass
    class Temple(Building): pass
    class Monastery(Temple): pass
    class Mosque(Temple): pass
    class BuddhistTemple(Temple): pass
    class Church(Temple): pass

    class NaturalLocation(Place): pass
    
    class WaterNaturalLocation(NaturalLocation): pass
    class River(WaterNaturalLocation): pass
    class Lake(WaterNaturalLocation): pass
    class Sea(WaterNaturalLocation): pass
    class Ocean(WaterNaturalLocation): pass
    
    class LandNaturalLocation(NaturalLocation): pass
    class Mountain(LandNaturalLocation): pass
    class Peak(LandNaturalLocation): pass
    class Volcano(LandNaturalLocation): pass
    class Desert(LandNaturalLocation): pass
    class Forest(LandNaturalLocation): pass
    class Island(LandNaturalLocation): pass

    # Data properties #14

    class population(DataProperty, FunctionalProperty):
        domain = [Country | Continent | PopulatedPlace]
        range  = [int]

    class name(DataProperty, FunctionalProperty):
        domain = [Thing]
        range  = [str]

    class height(DataProperty, FunctionalProperty):
        domain = [LandNaturalLocation | Landmark]
        range  = [float]

    class depth(DataProperty, FunctionalProperty):
        domain = [WaterNaturalLocation]
        range  = [float]

    class is_saltwatered(DataProperty, FunctionalProperty):
        domain = [WaterNaturalLocation]
        range  = [bool]

    class is_capital(DataProperty, FunctionalProperty):
        domain = [City]
        range  = [bool]

    class area(DataProperty, FunctionalProperty):
        domain = [Place | Country | Continent]
        range  = [float]

    class first_name(DataProperty, FunctionalProperty):
        domain = [Person]
        range  = [str]

    class last_name(DataProperty, FunctionalProperty):
        domain = [Person]
        range  = [str]

    class age(DataProperty, FunctionalProperty):
        domain = [Person]
        range  = [int]

    class construction_date(DataProperty, FunctionalProperty):
        domain = [Building]
        range  = [int]

    class is_tropical(DataProperty, FunctionalProperty):
        domain = [Forest]
        range  = [bool]

    class period(DataProperty, FunctionalProperty):
        domain = [Architecture]
        range  = [int]

    class temperature(DataProperty, FunctionalProperty):
        domain = [Place]
        range  = [float]

    # Object Properties #26
    class is_located_in(ObjectProperty, TransitiveProperty):
        domain = [Place | Country]
        range  = [Place | Country | Continent]

    class contains(ObjectProperty):
        domain = [Place | Country | Continent]
        range  = [Country | Place]
        inverse_property = is_located_in

    class is_peak_in(is_located_in):
        domain = [Peak]
        range  = [Mountain]

    class has_peak(ObjectProperty):
        domain = [Mountain]
        range  = [Peak]
        inverse_property = is_peak_in

    class is_island_in(is_located_in):
        domain = [Island]
        range  = [WaterNaturalLocation]

    class has_island(ObjectProperty):
        domain = [WaterNaturalLocation]
        range  = [Island]
        inverse_property = is_island_in

    class has_border_with(ObjectProperty, SymmetricProperty):
        domain = [Country]
        range  = [Country]

    class has_main_religion(ObjectProperty):
        domain = [Country]
        range  = [Religion]

    class is_main_religion_in(ObjectProperty):
        domain = [Religion]
        range  = [Country]
        inverse_property = has_main_religion

    class has_form_of_government(ObjectProperty):
        domain = [Country]
        range  = [Form_of_Government]

    class is_applied_in(ObjectProperty):
        domain = [Form_of_Government]
        range  = [Country]
        inverse_property = has_form_of_government

    class has_architecture(ObjectProperty):
        domain = [Building]
        range  = [Architecture]

    class is_architecture_of(ObjectProperty):
        domain = [Architecture]
        range  = [Building]
        inverse_property = has_architecture   

    class is_head_of_state(ObjectProperty):
        domain = [Person]
        range  = [Country]

    class has_head_of_state(ObjectProperty):
        domain = [Country]
        range  = [Person]
        inverse_property = is_head_of_state

    class is_mayor_of(ObjectProperty):
        domain = [Person]
        range  = [PopulatedPlace]

    class has_mayor(ObjectProperty):
        domain = [PopulatedPlace]
        range  = [Person]
        inverse_property = is_mayor_of

    class is_head_of_temple(ObjectProperty):
        domain = [Person]
        range  = [Temple]

    class has_head_of_temple(ObjectProperty):
        domain = [Temple]
        range  = [Person]  
        inverse_property = is_head_of_temple

    class is_created_by(ObjectProperty):
        domain = [Country]
        range  = [Person]  

    class has_created(ObjectProperty):
        domain = [Person]
        range  = [Country]  
        inverse_property = is_created_by

    class is_found_by(ObjectProperty):
        domain = [Continent]
        range  = [Person]  

    class has_found(ObjectProperty):
        domain = [Person]
        range  = [Continent]  
        inverse_property = is_found_by

    # Individuals #170
    europe = Continent("Europe", area=10180000.0, population=746000000)
    asia = Continent("Asia", area=44580000.0, population=4561000000)
    africa = Continent("Africa", area=30370000.0, population=1216000000)
    north_america = Continent("North_America", area=24710000.0, population=592000000)
    south_america = Continent("South_America", area=17840000.0, population=422500000)
    australia_cont = Continent("Australia_Continent", area=8600000.0, population=43000000)
    antarctica = Continent("Antarctica", area=14200000.0, population=1000)

    pacific = Ocean("Pacific_Ocean", depth=11022, is_saltwatered=True)
    atlantic = Ocean("Atlantic_Ocean", depth=8376, is_saltwatered=True)
    indian = Ocean("Indian_Ocean", depth=7450, is_saltwatered=True)
    southern = Ocean("Southern_Ocean", depth=7235, is_saltwatered=True)
    arctic = Ocean("Arctic_Ocean", depth=5450, is_saltwatered=True)

    orthodoxy = Religion("Eastern_Orthodoxy")
    catholicism = Religion("Catholicism")
    protestantism = Religion("Protestantism")
    islam_sunni = Religion("Islam_Sunni")
    islam_shia = Religion("Islam_Shia")
    buddhism_zen = Religion("Zen_Buddhism")
    buddhism_theravada = Religion("Theravada_Buddhism")
    shintoism = Religion("Shintoism")
    hinduism = Religion("Hinduism")

    republic = Form_of_Government("Parliamentary_Republic")
    fed_republic = Form_of_Government("Federal_Republic")
    const_monarchy = Form_of_Government("Constitutional_Monarchy")
    abs_monarchy = Form_of_Government("Absolute_Monarchy")
    theocracy = Form_of_Government("Theocracy")
    one_party_state = Form_of_Government("Single_Party_State")

    gothic = Architecture("Gothic_Architecture", period=1200)
    baroque = Architecture("Baroque_Architecture", period=1600)
    renaissance = Architecture("Renaissance_Architecture", period=1450)
    modernism = Architecture("Modernism_Architecture", period=1900)
    brutalism = Architecture("Brutalism_Architecture", period=1950)
    byzantine = Architecture("Byzantine_Architecture", period=500)

    bulgaria = Country("Bulgaria", is_located_in=[europe], population=6500000, has_main_religion=[orthodoxy], has_form_of_government=[republic])
    sofia = City("Sofia", is_located_in=[bulgaria], is_capital=True, population=1200000)
    rumen_radev = Person("Rumen_Radev", first_name="Rumen", last_name="Radev", age=62)
    bulgaria.has_head_of_state = [rumen_radev]
    vasil_terziev = Person("Vasil_Terziev", first_name="Vasil", last_name="Terziev", age=46)
    sofia.has_mayor = [vasil_terziev]

    france = Country("France", is_located_in=[europe], population=67000000, has_form_of_government=[republic])
    paris = City("Paris", is_located_in=[france], is_capital=True, population=2100000)
    emmanuel_macron = Person("Emmanuel_Macron", first_name="Emmanuel", last_name="Macron", age=46)
    france.has_head_of_state = [emmanuel_macron]

    japan = Country("Japan", is_located_in=[asia], population=125000000, has_form_of_government=[const_monarchy], has_main_religion=[shintoism])
    tokyo = City("Tokyo", is_located_in=[japan], is_capital=True, population=14000000)
    kyoto = City("Kyoto", is_located_in=[japan], population=1470000)
    naruhito = Person("Emperor_Naruhito", first_name="Naruhito", age=63)
    japan.has_head_of_state = [naruhito]

    usa = Country("USA", is_located_in=[north_america], population=331000000, has_form_of_government=[fed_republic])
    washington = City("Washington_DC", is_located_in=[usa], is_capital=True, population=700000)
    donald_trump = Person("Donald_Trump", first_name="Donald", last_name="Trump", age=81)
    usa.has_head_of_state = [donald_trump]

    germany = Country("Germany", is_located_in=[europe], population=83000000, has_form_of_government=[fed_republic])
    berlin = City("Berlin", is_located_in=[germany], is_capital=True, population=3700000)
    frank_walter = Person("Frank_Walter_Steinmeier", first_name="Frank-Walter", last_name="Steinmeier", age=70)
    germany.has_head_of_state = [frank_walter]

    united_kingdom = Country("United_Kingdom", is_located_in=[europe], population=67000000, has_form_of_government=[const_monarchy])
    london = City("London", is_located_in=[united_kingdom], is_capital=True, population=8900000)
    king_charles = Person("King_Charles_III", first_name="Charles", last_name="Windsor", age=75)
    united_kingdom.has_head_of_state = [king_charles]

    spain = Country("Spain", is_located_in=[europe], population=47000000, has_form_of_government=[const_monarchy], has_main_religion=[catholicism])
    madrid = City("Madrid", is_located_in=[spain], is_capital=True, population=3300000)
    felipe_vi = Person("King_Felipe_VI", first_name="Felipe", age=56)
    spain.has_head_of_state = [felipe_vi]

    austria = Country("Austria", is_located_in=[europe], population=9000000, has_form_of_government=[republic])
    vienna = City("Vienna", is_located_in=[austria], is_capital=True, population=1900000)

    switzerland = Country("Switzerland", is_located_in=[europe], population=8700000, has_form_of_government=[fed_republic])
    bern = City("Bern", is_located_in=[switzerland], is_capital=True, population=133000)

    china = Country("China", is_located_in=[asia], population=1412000000, has_form_of_government=[one_party_state])
    beijing = City("Beijing", is_located_in=[china], is_capital=True, population=21500000)
    xi_jinping = Person("Xi_Jinping", first_name="Jinping", last_name="Xi", age=70)
    china.has_head_of_state = [xi_jinping]

    south_korea = Country("South_Korea", is_located_in=[asia], population=51000000, has_form_of_government=[republic])
    seoul = City("Seoul", is_located_in=[south_korea], is_capital=True, population=9700000)

    thailand = Country("Thailand", is_located_in=[asia], population=71000000, has_form_of_government=[const_monarchy], has_main_religion=[buddhism_theravada])
    bangkok = City("Bangkok", is_located_in=[thailand], is_capital=True, population=10500000)

    saudi_arabia = Country("Saudi_Arabia", is_located_in=[asia], population=35000000, has_form_of_government=[abs_monarchy], has_main_religion=[islam_sunni])
    riyadh = City("Riyadh", is_located_in=[saudi_arabia], is_capital=True, population=7600000)

    israel = Country("Israel", is_located_in=[asia], population=9300000, has_form_of_government=[republic])
    jerusalem = City("Jerusalem", is_located_in=[israel], is_capital=True, population=936000)

    egypt = Country("Egypt", is_located_in=[africa], population=109000000, has_form_of_government=[republic], has_main_religion=[islam_sunni])
    cairo = City("Cairo", is_located_in=[egypt], is_capital=True, population=9600000)

    south_africa = Country("South_Africa", is_located_in=[africa], population=60000000, has_form_of_government=[republic])
    pretoria = City("Pretoria", is_located_in=[south_africa], is_capital=True, population=2500000)

    morocco = Country("Morocco", is_located_in=[africa], population=37000000, has_form_of_government=[const_monarchy], has_main_religion=[islam_sunni])
    rabat = City("Rabat", is_located_in=[morocco], is_capital=True, population=575000)

    canada = Country("Canada", is_located_in=[north_america], population=38000000, has_form_of_government=[const_monarchy])
    ottawa = City("Ottawa", is_located_in=[canada], is_capital=True, population=1000000)

    mexico = Country("Mexico", is_located_in=[north_america], population=128000000, has_form_of_government=[fed_republic])
    mexico_city = City("Mexico_City", is_located_in=[mexico], is_capital=True, population=8900000)

    brazil = Country("Brazil", is_located_in=[south_america], population=214000000, has_form_of_government=[fed_republic])
    brasilia = City("Brasilia", is_located_in=[brazil], is_capital=True, population=3000000)

    argentina = Country("Argentina", is_located_in=[south_america], population=45000000, has_form_of_government=[republic])
    buenos_aires = City("Buenos_Aires", is_located_in=[argentina], is_capital=True, population=2890000)

    chile = Country("Chile", is_located_in=[south_america], population=19000000, has_form_of_government=[republic])
    santiago = City("Santiago", is_located_in=[chile], is_capital=True, population=6200000)

    australia_country = Country("Australia_Country", is_located_in=[australia_cont], population=25700000, has_form_of_government=[const_monarchy])
    canberra = City("Canberra", is_located_in=[australia_country], is_capital=True, population=431000)

    new_zealand = Country("New_Zealand", is_located_in=[australia_cont], population=5100000, has_form_of_government=[const_monarchy])
    wellington = City("Wellington", is_located_in=[new_zealand], is_capital=True, population=215000)

    serbia = Country("Serbia", is_located_in=[europe], population=6800000)
    belgrade = City("Belgrade", is_located_in=[serbia], is_capital=True, population=1166000)

    romania = Country("Romania", is_located_in=[europe], population=19000000)
    bucharest = City("Bucharest", is_located_in=[romania], is_capital=True, population=1800000)

    rila = Mountain("Rila", is_located_in=[bulgaria])
    musala = Peak("Musala", is_peak_in=[rila], height=2925.0)
    pirin = Mountain("Pirin", is_located_in=[bulgaria])
    vihren = Peak("Vihren", is_peak_in=[pirin], height=2914.0)
    himalayas = Mountain("Himalayas", is_located_in=[asia])
    everest = Peak("Everest", is_peak_in=[himalayas], height=8848.0)
    himalayas.has_peak = [everest]
    alps = Mountain("Alps", is_located_in=[europe])
    mont_blanc = Peak("Mont_Blanc", is_peak_in=[alps], height=4810.0)
    andes = Mountain("Andes", is_located_in=[south_america])
    aconcagua = Peak("Aconcagua", is_peak_in=[andes], height=6961.0)

    danube = River("Danube_River", is_located_in=[europe], depth=25.0, is_saltwatered=False)
    nile = River("Nile_River", is_located_in=[africa], depth=15.0, is_saltwatered=False)
    amazon = River("Amazon_River", is_located_in=[south_america], is_saltwatered=False, depth=100.0)
    iskar = River("Iskar_River", is_located_in=[bulgaria], depth=75.0, is_saltwatered=False)
    black_sea = Sea("Black_Sea", is_located_in=[europe], is_saltwatered=True, depth=2212.0)
    mediterranean = Sea("Mediterranean_Sea", is_located_in=[europe], is_saltwatered=True)
    lake_baikal = Lake("Lake_Baikal", is_located_in=[asia], depth=1642.0, is_saltwatered=False)
    lake_victoria = Lake("Lake_Victoria", is_located_in=[africa], depth=83.0, is_saltwatered=False)

    madagascar_isl = Island("Madagascar_Island", is_located_in=[africa])
    sicily = Island("Sicily", is_located_in=[mediterranean])
    greenland = Island("Greenland", is_located_in=[north_america], area=2166000.0)
    tasmania = Island("Tasmania", is_located_in=[australia_cont])
    boracay = Island("Boracay", is_island_in=[pacific], temperature=28.0)

    sahara = Desert("Sahara_Desert", is_located_in=[africa], area=9200000.0, temperature=45.0)
    gobi = Desert("Gobi_Desert", is_located_in=[asia], area=1295000.0, temperature=20.0)
    atacama = Desert("Atacama_Desert", is_located_in=[south_america])
    amazon_forest = Forest("Amazon_Rainforest", is_located_in=[south_america], is_tropical=True)
    sherwood = Forest("Sherwood_Forest", is_located_in=[europe], is_tropical=False)
    vitosha_forest = Forest("Vitosha_Forest", is_located_in=[bulgaria])

    etna = Volcano("Etna", is_located_in=[sicily], height=3357.0)
    vesuvius = Volcano("Vesuvius", is_located_in=[italy := Country("Italy", is_located_in=[europe])], height=1281.0)
    fuji = Volcano("Mount_Fuji", is_located_in=[japan], height=3776.0)

    rila_monastery = Monastery("Rila_Monastery", is_located_in=[rila], construction_date=927)
    rila_monastery.has_architecture = [byzantine]
    st_ivan_rilski = Person("St_Ivan_Rilski")
    rila_monastery.has_head_of_temple = [st_ivan_rilski]

    tsarevets = Castle("Tsarevets_Fortress", is_located_in=[bulgaria], construction_date=1185)
    eiffel_tower = CulturalLandmark("Eiffel_Tower", is_located_in=[paris], height=330.0)
    colosseum = CulturalLandmark("Colosseum", is_located_in=[rome := City("Rome", is_located_in=[italy], is_capital=True)])
    notre_dame = Church("Notre_Dame_de_Paris", is_located_in=[paris], construction_date=1163)
    notre_dame.has_architecture = [gothic]
    
    taj_mahal = Temple("Taj_Mahal", is_located_in=[india := Country("India", is_located_in=[asia])], construction_date=1632)
    blue_mosque = Mosque("Blue_Mosque", is_located_in=[istanbul := City("Istanbul", is_located_in=[turkey := Country("Turkey", is_located_in=[asia])])])
    kinkaku_ji = BuddhistTemple("Kinkaku_ji", is_located_in=[kyoto])

    zheravna = Village("Zheravna", is_located_in=[bulgaria], population=400)
    monaco_city = City("Monaco_City", is_located_in=[monaco := Country("Monaco", is_located_in=[europe])], is_capital=True)
    pope_leo = Person("Pope_Leo_XIV", first_name="Robert", last_name="Prevost", age=69)
    vatican_temple = Temple("St_Peters_Basilica", is_located_in=[vatican := Country("Vatican", is_located_in=[europe])])
    vatican_temple.has_head_of_temple = [pope_leo]

    greece = Country("Greece", is_located_in=[europe])
    bulgaria.has_border_with = [greece, turkey, romania, serbia]

    columbus = Person("Christopher_Columbus")
    columbus.has_found = [north_america]
    vasco_da_gama = Person("Vasco_da_Gama")
    vasco_da_gama.has_found = [asia]

    # Equivalent Classes #18
    class EuropeanCountry(Country):
        equivalent_to = [Country & is_located_in.some(europe)]

    class AsianCountry(Country):
        equivalent_to = [Country & is_located_in.some(asia)]

    class AbsMonarchyState(Country):
        equivalent_to = [Country & has_form_of_government.some(abs_monarchy)]

    class RepublicState(Country):
        equivalent_to = [Country & has_form_of_government.some(OneOf([republic, fed_republic]))]

    class OrthodoxChristianCountry(Country):
        equivalent_to = [Country & has_main_religion.some(orthodoxy)]

    class SunniIslamicCountry(Country):
        equivalent_to = [Country & has_main_religion.some(islam_sunni)]

    class ShiaIslamicCountry(Country):
        equivalent_to = [Country & has_main_religion.some(islam_shia)]

    class Megacity(City):
        equivalent_to = [City & population.some(ConstrainedDatatype(int, min_inclusive = 10000000))]

    class SmallVillage(Village):
        equivalent_to = [Village & population.some(ConstrainedDatatype(int, max_inclusive = 500))]

    class HighPeak(Peak):
        equivalent_to = [Peak & height.some(ConstrainedDatatype(float, min_inclusive = 8000.0))]

    class DeepWater(WaterNaturalLocation):
        equivalent_to = [WaterNaturalLocation & depth.some(ConstrainedDatatype(float, min_inclusive = 5000.0))]

    class TropicalIsland(Island):
        equivalent_to = [Island & is_island_in.some(Ocean) & temperature.some(ConstrainedDatatype(float, min_inclusive = 25.0))]

    class AncientBuilding(Building):
        equivalent_to = [Building & construction_date.some(ConstrainedDatatype(int, max_inclusive = 1000))]

    class ModernMetropolis(City):
        equivalent_to = [City & contains.some(Building & has_architecture.some(modernism))]

    class GothicTemple(Temple):
        equivalent_to = [Temple & has_architecture.some(gothic)]

    class SaltWaterBody(WaterNaturalLocation):
        equivalent_to = [WaterNaturalLocation & is_saltwatered.value(True)]

    class LandlockedCountry(Country):
        equivalent_to = [Country & Not(contains.some(Sea | Ocean))]

    class MountainousCountry(Country):
        equivalent_to = [Country & contains.some(Mountain)]

    class CapitalCity(City):
        equivalent_to = [City & is_capital.value(True)]

    AllDisjoint([City, Village])
    AllDisjoint([Mountain, Peak, Volcano, Desert, Forest, Island])
    AllDisjoint([River, Lake, Sea, Ocean])
    AllDisjoint([NaturalLocation, Landmark, PopulatedPlace])

# Reasoning
try:
    with onto:
        sync_reasoner_hermit(infer_property_values = True)
    print("Success! The ontology is consistent!")
except Exception as e:
    print(f"Error with the reasoner: {e}")

onto.save(file="GeoOntology.owl", format="rdfxml")