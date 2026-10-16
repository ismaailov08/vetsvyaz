"""Команда: python manage.py seed_full — расширенная база животных с историей болезней.

Добавляет ещё два хозяйства, третьего врача и 24 животных. Для больных и уже вылеченных
животных создаются завершённые консультации с диагнозами, заключениями и назначениями.
Команду можно запускать повторно: уже существующие записи не дублируются.
"""
from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models.signals import post_save
from django.utils import timezone

from accounts.models import Farmer, User, Vet
from consultations.models import Consultation, Prescription
from consultations.signals import consultation_saved
from farms.models import Animal, Vaccination

PASSWORD = "vet12345"

FARMERS = {
    "farmer": ("Ерлан", "Тулегенов", "КХ «Аксу»", "Байзакский район, Жамбылская обл.", "+7 701 555 12 34"),
    "farmer2": ("Айгерим", "Нурланова", "КХ «Береке»", "Таласский район, Жамбылская обл.", "+7 702 410 33 21"),
    "farmer3": ("Бауыржан", "Сапаров", "КХ «Жайлау»", "Меркенский район, Жамбылская обл.", "+7 705 902 18 77"),
}
VETS = {
    "vet": ("Арман", "Жумабеков", "Крупный рогатый скот", "ВЕТ-0412"),
    "vet2": ("Динара", "Касымова", "Мелкий рогатый скот", "ВЕТ-0577"),
    "vet3": ("Серик", "Абенов", "Лошади и верблюды", "ВЕТ-0631"),
}

# Эпизод болезни: (дней назад, врач, формат, жалоба, диагноз, заключение, [(препарат, доза, дней, ожидание)])
MASTITIS = ("vet", "video", "Уплотнение и жар в задней левой доле вымени, молоко с хлопьями, удой упал на треть",
            "Серозный мастит задней левой доли",
            "Сдаивать поражённую долю каждые 3 часа, молоко утилизировать. Массаж вымени, ограничить сочные корма.",
            [("Мастиет форте", "1 шприц в поражённую долю 2 раза в сутки", 4, 5)])
PNEUMONIA = ("vet", "visit", "Телёнок кашляет, из носа слизь, дышит часто, температура 40,6",
             "Бронхопневмония телят",
             "Изолировать в тёплом помещении без сквозняков, выпаивать тёплой водой, контроль температуры 2 раза в день.",
             [("Нитокс 200 (окситетрациклин)", "1 мл на 10 кг в/м, повтор через 72 ч", 6, 28),
              ("Флуниксин", "2 мл на 45 кг в/м 1 раз в сутки", 3, 7)])
DYSPEPSIA = ("vet", "chat", "Понос жёлто-серого цвета, телёнок вялый, плохо сосёт",
             "Диспепсия новорождённых телят, обезвоживание лёгкой степени",
             "Пропустить одно выпаивание молозива, вместо него регидратационный раствор. Чистая сухая подстилка.",
             [("Регидратационный раствор", "2 л тёплого раствора 3 раза в день", 3, 0),
              ("Энрофлон 5%", "1 мл на 20 кг п/к 1 раз в сутки", 3, 11)])
KETOSIS = ("vet", "video", "Через 3 недели после отёла плохо ест, удой снизился, запах ацетона изо рта",
           "Кетоз (ацетонемия)",
           "Сбалансировать рацион по энергии, добавить концентраты постепенно, ежедневный моцион.",
           [("Пропиленгликоль", "300 мл внутрь 1 раз в сутки", 5, 0),
            ("Глюкоза 40%", "500 мл в/в медленно", 2, 0)])
ENDOMETRITIS = ("vet", "visit", "Через 10 дней после отёла гнойные выделения из половых путей",
                "Послеродовой гнойно-катаральный эндометрит",
                "Ректальный контроль через 14 дней. Осеменение не раньше чем через 60 дней.",
                [("Метрикур", "1 шприц внутриматочно однократно", 1, 0)])
HOOF = ("vet", "video", "Хромает на левую переднюю ногу, между копытцами покраснение и неприятный запах",
        "Пододерматит (воспаление основы кожи копыта)",
        "Расчистить копыто, ванночки с медным купоросом через день, держать на сухой подстилке.",
        [("Тетрациклиновый спрей", "на поражённое копыто 2 раза в день", 7, 0)])
PIROPLASMOSIS = ("vet", "visit", "После пастбища высокая температура 41,2, моча красноватая, слизистые бледные",
                 "Пироплазмоз (подтверждён мазком крови)",
                 "Обработать всё стадо от клещей, ограничить выпас на заклещёванных участках.",
                 [("Азидин", "3,5 мг на кг в/м однократно", 1, 20),
                  ("Витамин B12", "10 мл в/м через день", 5, 0)])
BRUCELLA = ("vet", "visit", "Аборт на 7-м месяце стельности, плод мёртвый",
            "Подозрение на бруцеллёз, кровь направлена на РБП и РСК",
            "Карантин до получения результатов. Плод и послед сдать в ветлабораторию, место обработать дезраствором. "
            "Молоко не использовать.", [])
TRICHOPHYTIA = ("vet", "chat", "На голове и шее телёнка круглые пятна без шерсти, корочки",
                "Трихофития (стригущий лишай)",
                "Изолировать, корочки размягчать и удалять, инвентарь дезинфицировать. Работать в перчатках.",
                [("Вакцина ЛТФ-130 (лечебная доза)", "в/м двукратно с интервалом 14 дней", 14, 0)])
TYMPANY = ("vet", "video", "После выпаса на люцерне раздуло левый бок, беспокоится",
           "Острая тимпания рубца",
           "Поставить передними ногами на возвышение, массаж левой голодной ямки, 12 ч голодная диета.",
           [("Тимпанол", "150 мл в 1 л воды внутрь однократно", 1, 0)])
FASCIOLA = ("vet2", "visit", "Овцы худеют, отёки под нижней челюстью, шерсть тусклая",
            "Фасциолёз (по результатам копроскопии)",
            "Не пасти на заболоченных участках. Повторная дегельминтизация всего поголовья через 3 месяца.",
            [("Альбендазол 10%", "1 мл на 10 кг внутрь однократно", 1, 14)])
FOOTROT = ("vet2", "video", "Несколько овец хромают, между копытцами мокнущие язвы с запахом",
           "Копытная гниль (некробактериоз) овец",
           "Обрезка копыт, ножные ванны 2 раза в неделю, перевод на сухое пастбище.",
           [("Ванна с 10% сульфатом цинка", "прогон через ванну 5 минут", 5, 0),
            ("Окситетрациклин 20%", "1 мл на 10 кг в/м", 3, 21)])
COCCIDIOSIS = ("vet2", "chat", "Козлята с поносом, иногда с кровью, отстают в росте",
               "Эймериоз (кокцидиоз) козлят",
               "Ежедневная уборка навоза, сухая подстилка, кормушки поднять над полом.",
               [("Байкокс 5%", "1 мл на 2,5 кг внутрь однократно", 1, 63)])
SHEEP_PNEUM = ("vet2", "visit", "Овца кашляет, из носа выделения, температура 40,9",
               "Пастереллёз овец (подтверждён лабораторно)",
               "Изолировать больных, вакцинировать остальное поголовье, продезинфицировать кошару.",
               [("Нитокс 200", "1 мл на 10 кг в/м", 3, 28)])
STRANGLES = ("vet3", "visit", "Жеребец с гнойным истечением из носа, подчелюстные лимфоузлы увеличены, температура 40,1",
             "Мыт (стрептококковая инфекция лошадей)",
             "Изолировать, тёплые компрессы на лимфоузлы, мягкий влажный корм. Инвентарь отдельный.",
             [("Бензилпенициллин", "20 тыс. ЕД на кг в/м 2 раза в сутки", 7, 0)])
COLIC = ("vet3", "video", "Лошадь беспокоится, оглядывается на живот, ложится и катается",
         "Спастические колики",
         "Выводить шагом, не давать корм 12 ч, воду небольшими порциями. Сменить сено на качественное.",
         [("Флуниксин", "1,1 мг на кг в/в однократно", 1, 0)])
CAMEL_MANGE = ("vet3", "visit", "У верблюда зуд, расчёсы и корки на шее и боках, шерсть выпадает",
               "Саркоптоз (чесотка) верблюдов",
               "Обработать всё поголовье, место содержания обработать акарицидом.",
               [("Ивермектин 1%", "1 мл на 50 кг п/к, повтор через 10 дней", 2, 28)])
KERATITIS = ("vet", "chat", "Глаз слезится, роговица мутная, корова щурится на солнце",
             "Инфекционный кератоконъюнктивит",
             "Затенить место содержания, борьба с мухами, промывать глаз 2 раза в день.",
             [("Тетрациклиновая глазная мазь", "закладывать за веко 3 раза в день", 5, 0)])


def ep(days_ago, template):
    vet, kind, complaint, diagnosis, conclusion, rx = template
    return (days_ago, vet, kind, complaint, diagnosis, conclusion, rx)


# фермер, кличка, бирка, вид, порода, пол, дата рождения, вес, статус, эпизоды болезней
ANIMALS = [
    ("farmer2", "Алтынай", "KZ 0731 1001", "cattle", "Алатауская", "F", date(2020, 2, 11), 520, "treatment",
     [ep(400, ENDOMETRITIS), ep(3, MASTITIS)]),
    ("farmer2", "Карлыгаш", "KZ 0731 1002", "cattle", "Голштинская", "F", date(2019, 5, 3), 610, "treatment",
     [ep(5, KETOSIS)]),
    ("farmer2", "Бота", "KZ 0731 1003", "cattle", "Казахская белоголовая", "M", date(2026, 7, 20), 95, "treatment",
     [ep(2, PNEUMONIA)]),
    ("farmer2", "Шолпан", "KZ 0731 1004", "cattle", "Алатауская", "F", date(2021, 4, 8), 495, "quarantine",
     [ep(4, BRUCELLA)]),
    ("farmer2", "Майя", "KZ 0731 1005", "cattle", "Симментальская", "F", date(2018, 9, 15), 580, "healthy",
     [ep(210, HOOF), ep(95, KERATITIS)]),
    ("farmer2", "Тайлак", "KZ 0731 1006", "cattle", "Алатауская", "M", date(2026, 8, 30), 60, "healthy",
     [ep(30, DYSPEPSIA)]),
    ("farmer2", "Ақсұлу", "KZ 0731 1007", "cattle", "Голштинская", "F", date(2022, 1, 19), 540, "healthy",
     [ep(160, TYMPANY)]),
    ("farmer2", "Айша", "KZ 0731 1008", "goat", "Зааненская", "F", date(2023, 3, 2), 55, "healthy", []),
    ("farmer2", "Лақ", "KZ 0731 1009", "goat", "Местная пуховая", "M", date(2026, 4, 12), 14, "treatment",
     [ep(6, COCCIDIOSIS)]),
    ("farmer2", "Бұлбұл", "KZ 0731 1010", "goat", "Зааненская", "F", date(2026, 3, 28), 16, "healthy",
     [ep(40, COCCIDIOSIS)]),
    ("farmer3", "Қаракөз", "KZ 0844 2001", "sheep", "Эдильбаевская", "F", date(2022, 2, 25), 72, "treatment",
     [ep(8, FASCIOLA)]),
    ("farmer3", "Ақтоқты", "KZ 0844 2002", "sheep", "Казахская курдючная", "F", date(2021, 3, 1), 68, "treatment",
     [ep(4, FOOTROT)]),
    ("farmer3", "Серке", "KZ 0844 2003", "sheep", "Эдильбаевская", "M", date(2020, 1, 14), 98, "healthy",
     [ep(120, FASCIOLA)]),
    ("farmer3", "Марал", "KZ 0844 2004", "sheep", "Казахская тонкорунная", "F", date(2023, 2, 10), 58, "healthy", []),
    ("farmer3", "Боз", "KZ 0844 2005", "sheep", "Эдильбаевская", "F", date(2022, 12, 5), 64, "treatment",
     [ep(3, SHEEP_PNEUM)]),
    ("farmer3", "Сұңқар", "KZ 0844 2006", "horse", "Кушумская", "M", date(2017, 4, 22), 480, "treatment",
     [ep(300, COLIC), ep(5, STRANGLES)]),
    ("farmer3", "Жұлдыз", "KZ 0844 2007", "horse", "Казахская жабе", "F", date(2019, 6, 9), 430, "healthy",
     [ep(60, COLIC)]),
    ("farmer3", "Арғымақ", "KZ 0844 2008", "horse", "Ахалтекинская", "M", date(2016, 5, 17), 450, "healthy", []),
    ("farmer3", "Нар", "KZ 0844 2009", "camel", "Казахский бактриан", "M", date(2015, 3, 30), 690, "treatment",
     [ep(7, CAMEL_MANGE)]),
    ("farmer3", "Інген", "KZ 0844 2010", "camel", "Казахский бактриан", "F", date(2017, 2, 18), 610, "healthy",
     [ep(180, CAMEL_MANGE)]),
    ("farmer3", "Сарыбел", "KZ 0844 2011", "cattle", "Казахская белоголовая", "F", date(2020, 3, 7), 470, "treatment",
     [ep(6, PIROPLASMOSIS)]),
    ("farmer3", "Тентек", "KZ 0844 2012", "cattle", "Казахская белоголовая", "M", date(2026, 6, 1), 110, "treatment",
     [ep(9, TRICHOPHYTIA)]),
    ("farmer", "Аққұлақ", "KZ 0217 4620", "cattle", "Алатауская", "F", date(2026, 8, 14), 70, "healthy",
     [ep(25, DYSPEPSIA)]),
    ("farmer", "Көкжал", "KZ 0412 0110", "sheep", "Эдильбаевская", "M", date(2022, 4, 4), 90, "healthy",
     [ep(150, FOOTROT)]),
]

# прошлые болезни для животных из базового набора seed_demo
EXTRA_HISTORY = [
    ("KZ 0217 4591", ep(130, ENDOMETRITIS)),   # Маржан
    ("KZ 0519 2214", ep(75, KERATITIS)),       # Ночка
    ("KZ 0412 0081", ep(110, FASCIOLA)),       # Акбас
    ("KZ 0605 3307", ep(240, COLIC)),          # Тулпар
]

VACCINES = {
    "cattle": ("Ящур (ФМД)", 180), "sheep": ("Оспа овец", 365), "goat": ("Оспа коз", 365),
    "horse": ("Сибирская язва", 365), "camel": ("Сибирская язва", 365),
}


# Дополнительные хозяйства: поголовье генерируется по списку (вид: количество)
EXTRA_FARMS = [
    ("farmer4", "Нурлан", "Ахметов", "КХ «Тоғыз»", "Байзакский район, Жамбылская обл.", "+7 707 311 45 90",
     "0951", {"cattle": 7, "sheep": 9, "horse": 2}),
    ("farmer5", "Гүлнұр", "Есенова", "КХ «Сарыарқа»", "Таласский район, Жамбылская обл.", "+7 701 228 64 15",
     "0962", {"sheep": 12, "goat": 5, "cattle": 3}),
    ("farmer6", "Ержан", "Қалиев", "ТОО «Мерке-Агро»", "Меркенский район, Жамбылская обл.", "+7 778 640 02 33",
     "0973", {"cattle": 10, "horse": 3}),
    ("farmer7", "Сәуле", "Бекова", "КХ «Бірлік»", "Жуалынский район, Жамбылская обл.", "+7 747 105 77 61",
     "0984", {"sheep": 8, "goat": 4, "camel": 2, "horse": 2}),
    # ── другие области Казахстана ──
    ("farmer8", "Асқар", "Мұратов", "КХ «Шелек-Агро»", "Енбекшиказахский район, Алматинская обл.", "+7 701 772 10 05",
     "1101", {"cattle": 14, "sheep": 10}),
    ("farmer9", "Жанар", "Төлеуова", "КХ «Есік»", "Енбекшиказахский район, Алматинская обл.", "+7 702 118 40 62",
     "1102", {"cattle": 8, "goat": 6, "horse": 3}),
    ("farmer10", "Мағжан", "Әбенов", "КХ «Алатау»", "Талгарский район, Алматинская обл.", "+7 705 300 21 48",
     "1103", {"cattle": 12, "horse": 4}),
    ("farmer11", "Дана", "Сейітова", "ТОО «Іле Сүт»", "Илийский район, Алматинская обл.", "+7 707 455 09 13",
     "1104", {"cattle": 18}),
    ("farmer12", "Бекзат", "Оспанов", "КХ «Сайрам»", "Сайрамский район, Туркестанская обл.", "+7 778 210 66 30",
     "1201", {"sheep": 16, "goat": 8, "cattle": 4}),
    ("farmer13", "Ләззат", "Құрманова", "КХ «Ленгер»", "Толебийский район, Туркестанская обл.", "+7 747 631 25 87",
     "1202", {"sheep": 12, "cattle": 6, "horse": 2}),
    ("farmer14", "Талғат", "Ибраев", "КХ «Дарбаза»", "Сарыагашский район, Туркестанская обл.", "+7 701 905 14 72",
     "1203", {"sheep": 14, "camel": 3, "goat": 5}),
    ("farmer15", "Айбек", "Жақсылықов", "ТОО «Астана-Мал»", "Целиноградский район, Акмолинская обл.", "+7 702 640 88 19",
     "1301", {"cattle": 16, "horse": 6}),
    ("farmer16", "Әсем", "Нұрболова", "КХ «Бурабай»", "Бурабайский район, Акмолинская обл.", "+7 705 117 52 04",
     "1302", {"horse": 10, "cattle": 5, "sheep": 6}),
    ("farmer17", "Руслан", "Ким", "ТОО «Тобыл Агро»", "Костанайский район, Костанайская обл.", "+7 707 820 43 66",
     "1401", {"cattle": 20}),
    ("farmer18", "Мейрам", "Сыздықов", "КХ «Қарқаралы»", "Каркаралинский район, Карагандинская обл.", "+7 778 334 70 21",
     "1501", {"sheep": 15, "horse": 6, "cattle": 4}),
    ("farmer19", "Ольга", "Петренко", "КХ «Алтай»", "Катон-Карагайский район, Восточно-Казахстанская обл.",
     "+7 747 255 18 90", "1601", {"horse": 12, "cattle": 6}),
    ("farmer20", "Сәкен", "Әлиев", "КХ «Сырдария»", "Жалагашский район, Кызылординская обл.", "+7 701 488 39 57",
     "1701", {"camel": 9, "sheep": 10, "goat": 4}),
]
NAMES = {
    "cattle": ["Ақбөкен", "Сұлу", "Қарагөз", "Мойыл", "Жібек", "Ару", "Бұрыл", "Дала", "Нұр", "Көктем", "Самал"],
    "sheep": ["Ақсақ", "Ботақан", "Қошқар", "Мақпал", "Тоқты", "Ақбас", "Қызыл", "Ақтөс", "Ала", "Мұнар", "Ұлпа",
              "Шұбар"],
    "goat": ["Ешкі", "Серке-2", "Мақта", "Ақылақ", "Бөрте"],
    "horse": ["Құла", "Жирен", "Тарлан"],
    "camel": ["Бура", "Мая"],
}
BREEDS = {"cattle": ["Казахская белоголовая", "Алатауская", "Голштинская"],
          "sheep": ["Эдильбаевская", "Казахская курдючная"], "goat": ["Зааненская", "Местная пуховая"],
          "horse": ["Кушумская", "Казахская жабе"], "camel": ["Казахский бактриан"]}
WEIGHT = {"cattle": 480, "sheep": 70, "goat": 50, "horse": 450, "camel": 650}
# какие болезни встречаются у вида (для истории и для текущего лечения)
SPECIES_EPISODES = {"cattle": [MASTITIS, HOOF, KERATITIS, KETOSIS], "sheep": [FASCIOLA, FOOTROT],
                    "goat": [COCCIDIOSIS], "horse": [COLIC, STRANGLES], "camel": [CAMEL_MANGE]}


class Command(BaseCommand):
    help = "Добавляет хозяйства по районам, животных с полной историей болезней и врача"

    @transaction.atomic
    def handle(self, *args, **options):
        # чтобы при загрузке не создавались сотни уведомлений, сигнал временно отключаем
        post_save.disconnect(consultation_saved, sender=Consultation)
        try:
            self._seed()
        finally:
            post_save.connect(consultation_saved, sender=Consultation)
        call_command("seed_twin", stdout=self.stdout)  # датчики и показания для цифрового двойника

    def _seed(self):
        farmers, vets = {}, {}
        for login, (fn, ln, farm, district, phone) in FARMERS.items():
            u, created = User.objects.get_or_create(username=login, defaults={
                "first_name": fn, "last_name": ln, "role": User.Role.FARMER, "phone": phone})
            if created:
                u.set_password(PASSWORD)
                u.save()
            farmers[login], _ = Farmer.objects.get_or_create(user=u, defaults={"farm_name": farm, "district": district})
        for login, (fn, ln, spec, lic) in VETS.items():
            u, created = User.objects.get_or_create(username=login, defaults={
                "first_name": fn, "last_name": ln, "role": User.Role.VET})
            if created:
                u.set_password(PASSWORD)
                u.save()
            vets[login], _ = Vet.objects.get_or_create(user=u, defaults={"specialization": spec, "license": lic})

        now = timezone.now().replace(minute=0, second=0, microsecond=0)
        new_animals = new_cons = 0

        def add_episode(animal, episode):
            nonlocal new_cons
            days, vet, kind, complaint, diagnosis, conclusion, rx = episode
            when = now - timedelta(days=days, hours=(animal.pk or 0) % 6)
            when = when.replace(hour=9 + (animal.pk or 0) % 8)
            if Consultation.objects.filter(animal=animal, diagnosis=diagnosis,
                                           scheduled_at__date=when.date()).exists():
                return
            c = Consultation.objects.create(farmer=animal.farmer, vet=vets[vet], animal=animal, kind=kind,
                                            scheduled_at=when, complaint=complaint, status="done",
                                            diagnosis=diagnosis, conclusion=conclusion)
            for drug, dose, d, wd in rx:
                Prescription.objects.create(consultation=c, drug=drug, dose=dose, days=d, withdrawal_days=wd)
            new_cons += 1

        for login, name, tag, sp, breed, sex, born, kg, status, episodes in ANIMALS:
            a, created = Animal.objects.get_or_create(tag=tag, defaults={
                "farmer": farmers[login], "name": name, "species": sp, "breed": breed, "sex": sex,
                "born": born, "weight_kg": kg, "status": status})
            if created:
                new_animals += 1
                vaccine, period = VACCINES[sp]
                done = date.today() - timedelta(days=(a.pk * 37) % period)
                Vaccination.objects.create(animal=a, vaccine=vaccine, done_on=done,
                                           next_on=done + timedelta(days=period), batch=f"С-{100 + a.pk}")
            for e in episodes:
                add_episode(a, e)

        # дополнительные хозяйства по районам
        for login, fn, ln, farm, district, phone, prefix, herd in EXTRA_FARMS:
            u, created = User.objects.get_or_create(username=login, defaults={
                "first_name": fn, "last_name": ln, "role": User.Role.FARMER, "phone": phone})
            if created:
                u.set_password(PASSWORD)
                u.save()
            f, _ = Farmer.objects.get_or_create(user=u, defaults={"farm_name": farm, "district": district})
            n = 0
            for sp, count in herd.items():
                for i in range(count):
                    n += 1
                    tag = f"KZ {prefix} {n:04d}"
                    name = NAMES[sp][i % len(NAMES[sp])] + ("" if i < len(NAMES[sp]) else f"-{i // len(NAMES[sp]) + 1}")
                    current = (n % 9 == 4)          # примерно каждое девятое животное сейчас болеет
                    a, created = Animal.objects.get_or_create(tag=tag, defaults={
                        "farmer": f, "name": name, "species": sp, "breed": BREEDS[sp][i % len(BREEDS[sp])],
                        "sex": "F" if i % 3 else "M",
                        "born": date(2026, 3, 1) - timedelta(days=200 + (n * 97) % 2400),
                        "weight_kg": WEIGHT[sp] + (n * 13) % 60 - 30,
                        "status": "treatment" if current else "healthy"})
                    if not created:
                        continue
                    new_animals += 1
                    vaccine, period = VACCINES[sp]
                    done = date.today() - timedelta(days=(a.pk * 37) % period)
                    Vaccination.objects.create(animal=a, vaccine=vaccine, done_on=done,
                                               next_on=done + timedelta(days=period), batch=f"С-{100 + a.pk}")
                    eps = SPECIES_EPISODES[sp]
                    if current:
                        add_episode(a, ep(2 + n % 6, eps[n % len(eps)]))
                    elif n % 4 == 0:                 # у части здоровых — болезнь в прошлом
                        add_episode(a, ep(40 + (n * 23) % 300, eps[(n // 4) % len(eps)]))

        # Many-to-Many: закрепляем врачей за хозяйствами по видам скота
        for f in Farmer.objects.all():
            kinds = set(f.animals.values_list("species", flat=True))
            if "cattle" in kinds:
                f.vets.add(vets["vet"])
            if kinds & {"sheep", "goat"}:
                f.vets.add(vets["vet2"])
            if kinds & {"horse", "camel"}:
                f.vets.add(vets["vet3"])

        for tag, e in EXTRA_HISTORY:
            a = Animal.objects.filter(tag=tag).first()
            if a:
                add_episode(a, e)

        self.stdout.write(self.style.SUCCESS(
            f"Готово: добавлено животных {new_animals}, завершённых консультаций {new_cons}. "
            f"Всего в базе: {Animal.objects.count()} животных, "
            f"{Consultation.objects.filter(status='done').count()} записей в истории болезней. "
            f"Хозяйств: {Farmer.objects.count()}. Новые логины: farmer2…farmer20, vet3 (пароль {PASSWORD})"))
