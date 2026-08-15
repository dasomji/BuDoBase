import { Printer } from 'lucide-react';

import { Button } from '../components/ui/button';
import allocationScreenshot from '../assets/documentation/allocation.webp';
import cleaningScreenshot from '../assets/documentation/cleaning.webp';
import dashboardScreenshot from '../assets/documentation/dashboard.webp';
import kidMoneyScreenshot from '../assets/documentation/kid-money.webp';
import kidScreenshot from '../assets/documentation/kid.webp';
import kidsScreenshot from '../assets/documentation/kids.webp';
import placesScreenshot from '../assets/documentation/places.webp';
import pocketScreenshot from '../assets/documentation/pocket.webp';

const chapters = [
  ['start', 'Start & Navigation'],
  ['dashboard', 'Dashboard'],
  ['erste-hilfe', 'Erste Hilfe'],
  ['listen', 'Listen'],
  ['drucken', 'Drucken'],
  ['kinder', 'Kinder-Detailansicht & Check-in'],
  ['taschengeld', 'Taschengeld'],
  ['schwerpunkte', 'Schwerpunkte'],
  ['happy-cleaning', 'Happy Cleaning'],
  ['auslagerorte', 'Auslagerorte'],
  ['spiele', 'Spiele'],
  ['team-turnus', 'Team & Turnus'],
  ['kueche', 'Küche'],
  ['orgi', 'Orgi-Funktionen'],
  ['abschluss', 'Am Ende des Turnus'],
];

function Contents({ compact = false }) {
  return (
    <nav aria-label="Inhaltsverzeichnis" className={compact ? 'rounded-xl border border-border bg-surface p-4 min-[901px]:hidden print:hidden' : 'sticky top-[calc(var(--app-header-height,0px)+1rem)] rounded-xl border border-border bg-surface p-4 shadow-sm print:hidden'}>
      <h2 className="mb-3 text-base font-semibold">Inhaltsverzeichnis</h2>
      <ol className="grid gap-1.5 text-sm">
        {chapters.map(([id, title], index) => (
          <li key={id}>
            <a className="flex gap-2 rounded-md px-2 py-1.5 text-link hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring" href={`#${id}`}>
              <span className="w-5 shrink-0 text-muted-foreground">{index + 1}.</span>
              <span>{title}</span>
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}

function Audience({ children = 'Für Betreuer:innen & Orgis' }) {
  return <span className="inline-flex rounded-full bg-secondary px-3 py-1 text-xs font-medium">{children}</span>;
}

function Section({ id, number, title, audience, children }) {
  return (
    <section className="scroll-mt-[calc(var(--app-header-height,0px)+1rem)] rounded-2xl border border-border bg-surface p-4 shadow-elevated backdrop-blur min-[901px]:p-6 print:rounded-none print:border-0 print:bg-white print:p-0 print:shadow-none print:backdrop-blur-none" id={id}>
      <div className="mb-5 flex flex-wrap items-center gap-3">
        <span className="grid size-9 shrink-0 place-items-center rounded-full bg-primary text-sm font-semibold" aria-hidden="true">{number}</span>
        <h2 className="text-2xl font-semibold tracking-tight">{title}</h2>
        <Audience>{audience}</Audience>
      </div>
      <div className="grid gap-5 leading-7">{children}</div>
      <p className="mt-6 text-right text-sm print:hidden"><a className="underline" href="#start">Zum Anfang</a></p>
    </section>
  );
}

function Subsection({ title, children }) {
  return (
    <div className="grid gap-2">
      <h3 className="text-lg font-semibold">{title}</h3>
      {children}
    </div>
  );
}

function Callout({ title, children, tone = 'blue' }) {
  const classes = tone === 'yellow'
    ? 'border-primary bg-warning text-warning-foreground'
    : 'border-border bg-muted';
  return (
    <aside className={`rounded-xl border p-4 ${classes}`}>
      <p className="font-semibold">{title}</p>
      <div className="mt-1 grid gap-2">{children}</div>
    </aside>
  );
}

function Screenshot({ src, alt, caption }) {
  return (
    <figure className="my-2 overflow-hidden rounded-xl border border-border bg-popover shadow-sm [break-inside:avoid]">
      <img className="block h-auto w-full" src={src} alt={alt} />
      <figcaption className="flex flex-wrap items-center gap-2 border-t border-border px-4 py-3 text-sm text-muted-foreground">
        <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">Synthetische Beispieldaten</span>
        <span>{caption}</span>
      </figcaption>
    </figure>
  );
}

function AppLink({ href, children }) {
  return <a className="font-medium underline decoration-secondary decoration-2 underline-offset-2" href={href}>{children}</a>;
}

export function DocumentationPage() {
  return (
    <main className="documentation-page !block" id="body-container">
      <div className="mx-auto grid w-full max-w-[92rem] gap-8 min-[901px]:grid-cols-[16rem_minmax(0,52rem)] min-[901px]:justify-center print:!grid-cols-1">
        <aside className="hidden min-[901px]:block print:hidden"><Contents /></aside>
        <article className="min-w-0 space-y-12">
          <header className="grid gap-5 rounded-2xl border border-border bg-surface p-4 shadow-elevated backdrop-blur min-[901px]:p-6 print:rounded-none print:border-0 print:bg-white print:p-0 print:shadow-none print:backdrop-blur-none" id="start">
            <div>
              <p className="mb-2 text-sm font-semibold tracking-wide text-muted-foreground uppercase">Handbuch für den Turnusalltag</p>
              <p className="text-3xl font-semibold tracking-tight min-[901px]:text-4xl">BuDoBase einfach nutzen</p>
            </div>
            <p className="max-w-3xl text-lg leading-8">Diese Dokumentation gibt Betreuer:innen und Organisator:innen einen Überblick darüber, welche Funktionen es in BuDoBase gibt, was das Team damit machen kann und wie die wichtigsten Abläufe funktionieren. Sie ist so aufgebaut, dass man sie vor dem Turnus gemeinsam durchgehen und während des Turnus als Nachschlagewerk verwenden kann.</p>
            <Contents compact />
            <Subsection title="Navigation und Turnuswechsel">
              <p>Am Handy erreichst du das Menü über den normalen Menü-Button, am Desktop steht es links als Sidebar. Ganz oben siehst du <strong>BuDoBase</strong>. Ein Klick darauf bringt dich jederzeit zurück zum Dashboard.</p>
              <p>Direkt darunter steht der aktuelle Turnus. Über das Wechsel-Symbol daneben kannst du einen anderen Turnus auswählen – etwa wenn du Daten aus einem früheren Turnus brauchst oder gerade in einem anderen Turnus arbeitest. Prüfe vor Eintragungen immer kurz, ob der richtige Turnus ausgewählt ist.</p>
              <p>Am Desktop kannst du die Sidebar mit <strong>⌘ B</strong> (Command-B; unter Windows und Linux mit <strong>Strg B</strong>) ein- und ausklappen. Dasselbe geht über das Sidebar-Symbol links neben dem Seitentitel. So lässt sich bei breiten Tabellen oder Detailansichten mehr Platz für den Inhalt schaffen.</p>
            </Subsection>
          </header>

          <Section id="dashboard" number="2" title="Dashboard" audience="Vor allem für Betreuer:innen">
            <p>Das Dashboard ist für Betreuer:innen gedacht, damit sie einen schnellen Überblick über die wichtigsten Dinge haben. Dort gibt es einen Gesamtüberblick über die Kinder, alle Notizen und – sofern das Team das Feature nutzt – alle EH-Einträge. Wie diese dokumentiert werden, steht im eigenen Abschnitt <AppLink href="#erste-hilfe">Erste Hilfe</AppLink>.</p>
            <Subsection title="Meine Familie, Schwerpunkte und Happy Cleaning">
              <p>Auf dem Dashboard siehst du auch die Kinder deiner eigenen BuDo-Familie. Das ist beispielsweise bei einem Feueralarm hilfreich, weil die Liste damit praktisch immer dabei ist und du nicht von einer Papierliste abhängig bist. Nicht anwesende Kinder haben ein <strong>❌</strong> hinter ihrem Namen, wodurch man in stressigen Situationen leichter den Überblick behält.</p>
              <p>Außerdem erscheinen die Kinder jener Schwerpunkte, für die du eingetragen bist. Beim Happy Cleaning siehst du die Kinder der Station, der du zugewiesen bist, sowie die To-Dos dieser Station. Aufgaben können direkt abgehakt werden, damit nichts Wichtiges vergessen wird.</p>
            </Subsection>
            <Screenshot src={dashboardScreenshot} alt="BuDoBase-Dashboard mit den synthetischen Kindern Harry Potter, Hermione Granger und Ron Weasley, Notiz, EH-Eintrag, Schwerpunkt- und Happy-Cleaning-Karten" caption="Dashboard mit Kinderüberblick, Aktivität, Familie, Schwerpunkten und Happy Cleaning." />
          </Section>

          <Section id="erste-hilfe" number="3" title="Erste Hilfe" audience="Für das gesamte Team">
            <Subsection title="Digital oder auf Papier">
              <p>Wichtig ist, dass sich das gesamte Team vor dem Turnus darauf einigt, ob Erste Hilfe auf Papier oder digital dokumentiert wird. Stefan ist damit einverstanden, das digitale Erste-Hilfe-Heft zu nutzen. Sein gewünschtes Ergebnis am Turnusende bleibt eine vollständige Dokumentation auf Papier oder als heruntergeladene PDF.</p>
              <p>Der große Vorteil der digitalen Erste Hilfe ist, dass Einträge auch an Auslagerorten oder irgendwo draußen gemacht werden können. Zusätzlich lassen sich Fotos hinzufügen. Das ist zum Beispiel hilfreich, wenn man einen Zeckenbiss dokumentieren und den Verlauf mit Bildern festhalten möchte.</p>
            </Subsection>
            <Subsection title="Einträge anlegen und wiederfinden">
              <p>EH-Einträge erscheinen einerseits gesammelt im Dashboard und andererseits beim jeweiligen Kind. Neue Maßnahmen werden in der <AppLink href="#kinder">Kinder-Detailansicht</AppLink> angelegt; dort können auch Fotos ergänzt werden. So liegt für jedes Kind die gesamte Erste-Hilfe-Dokumentation an einem Ort und niemand muss im Papierheft hin- und herspringen.</p>
            </Subsection>
            <Callout title="Teamentscheidung vor dem Start" tone="yellow">
              <p>Nicht parallel halb auf Papier und halb digital dokumentieren. Legt gemeinsam einen verbindlichen Weg fest. Wenn ihr BuDoBase nutzt, kann die gesamte EH-Dokumentation am Ende gedruckt oder als PDF gespeichert und Stefan übergeben werden.</p>
            </Callout>
          </Section>

          <Section id="listen" number="4" title="Listen" audience="Für das gesamte Team">
            <p>Unter <strong>Listen</strong> findest du Kinderlisten mit unterschiedlichen Schwerpunkten. Sie greifen auf dieselben Turnusdaten zu, bereiten sie aber jeweils für einen konkreten Arbeitsablauf auf.</p>
            <Subsection title="Alle Kinder">
              <p><AppLink href="/all_kids">Alle Kinder</AppLink> ist die umfangreiche Auflistung aller Kinder und bietet einen guten Gesamtüberblick. Die Tabelle enthält unter anderem BuDo-Familie, Geschlecht, Alter, Aufenthaltsdauer, Schwerpunkte, Geschwister, Zeltwunsch, Ernährung, Medikamente, gesundheitliche Informationen und Anmerkungen. Über das Filterfeld findest du ein Kind schnell; ein Klick auf den Namen öffnet die Kinder-Detailansicht.</p>
            </Subsection>
            <Screenshot src={kidsScreenshot} alt="Tabelle Alle Kinder mit ausschließlich synthetischen Harry-Potter-Namen und Beispieldaten" caption="„Alle Kinder“ ist die ausführlichste Übersicht und lässt sich nach Namen filtern." />
            <Subsection title="Gut zu wissen">
              <p>Unter <AppLink href="/gut-zu-wissen/">Gut zu wissen</AppLink> sind verschiedene Gruppen zusammengefasst: Geburtstagskinder, Einwöchige, Kinder, die das erste Mal im BuDo sind, Essen und Allergien, gesundheitliche Informationen sowie zusätzliche Anmerkungen der Eltern.</p>
              <p>Dort steht auch die Verabschiedungsliste für Kinder, die 15 oder 16 sind. Achtung: Die Liste zeigt ebenfalls Kinder, die knapp vor dem 15. Geburtstag stehen. So hat man sie am Schirm, falls sie beispielsweise im Turnus Geburtstag haben oder aus anderen Gründen verabschiedet werden sollen.</p>
            </Subsection>
            <Subsection title="Mörderspielliste">
              <p>Wenn ihr das Mörderspiel spielen wollt, könnt ihr als Turnus schlicht und ergreifend die <AppLink href="/murdergame">Mörderspielliste</AppLink> drucken. Darauf stehen alle anwesenden Kinder und alle anwesenden Betreuer:innen. Danach nur noch schneiden – und schon ist das Mörderspiel beisammen.</p>
            </Subsection>
            <Subsection title="Zuganreise und Zugabreise">
              <p>Die <AppLink href="/zuganreise">Zuganreiseliste</AppLink> und die <AppLink href="/zugabreise">Zugabreiseliste</AppLink> helfen zu überprüfen, ob Kinder eine angemeldete Zugreise tatsächlich in Anspruch nehmen. Über den Ja-Nein-Toggle kann eingetragen werden, ob ein Kind wirklich mitgefahren ist beziehungsweise mitfahren wird.</p>
              <p>Bei der Zugabreise können zusätzlich Abreiseinformationen und Notizen ergänzt werden – zum Beispiel, wenn ein Kind früher aussteigen möchte. Das muss natürlich immer mit den Eltern abgesprochen sein; in BuDoBase steht die Information danach direkt am richtigen Ort.</p>
            </Subsection>
          </Section>

          <Section id="drucken" number="5" title="Drucken" audience="Für das gesamte Team">
            <p>Alle Seiten, auf denen rechts oben neben dem Seitentitel ein <strong>Drucken</strong>-Button erscheint, besitzen eine vorbereitete Druckansicht. Am Handy wird derselbe Button als rundes Drucker-Symbol angezeigt. Im Druckdialog des Browsers kann die Ausgabe entweder auf Papier gedruckt oder als PDF gespeichert werden.</p>
            <Subsection title="Seiten mit Drucken-Button">
              <ul className="grid list-disc gap-2 pl-6">
                <li><AppLink href="/dokumentation/">Dokumentation</AppLink> – das gesamte Handbuch.</li>
                <li><AppLink href="/gut-zu-wissen/">Gut zu wissen</AppLink> – die zusammengefassten Kindergruppen und Hinweise.</li>
                <li><AppLink href="/murdergame">Mörderspielliste</AppLink> – Namen von anwesenden Kindern und Teammitgliedern zum Ausschneiden.</li>
                <li><AppLink href="/zuganreise">Zuganreise</AppLink> und <AppLink href="/zugabreise">Zugabreise</AppLink> – inklusive Anzahl der angemeldeten Kinder und Top-Jugend-Tickets. So ist sofort klar, für wie viele Kinder noch ein Ticket gebraucht wird.</li>
                <li><AppLink href="/budo_familien">BuDo-Familien</AppLink> – eine eigene Liste je Familie.</li>
                <li><AppLink href="/swp-einteilung-w1">SWP 1</AppLink> und <AppLink href="/swp-einteilung-w2">SWP 2</AppLink> – die jeweilige Schwerpunkt-Einteilung.</li>
                <li><AppLink href="/happy-cleaning/print/">Happy-Cleaning-Nummernliste</AppLink> – anwesende und abwesende Kinder mit beziehungsweise ohne Nummer.</li>
                <li><AppLink href="/kitchen">Küche</AppLink> – die Küchenübersicht und Menüplanung.</li>
              </ul>
            </Subsection>
            <p><strong>Alle Kinder</strong> ist bewusst nicht als Papierliste gedacht und besitzt deshalb keinen Drucken-Button. Der Serienbrief ist ein eigenständiges Druckdokument und wird im Abschnitt <AppLink href="#orgi">Orgi-Funktionen</AppLink> erklärt.</p>
          </Section>

          <Section id="kinder" number="6" title="Kinder-Detailansicht & Check-in" audience="Für Betreuer:innen und Orgis">
            <Subsection title="Ein Kind finden">
              <p>In der globalen Suchleiste kannst du nach Kindern und Auslagerorten suchen. Alternativ filterst du in „Alle Kinder“ nach dem Namen. Ein Klick auf einen Kindernamen führt zur Kinder-Detailansicht.</p>
            </Subsection>
            <Subsection title="Alle Informationen an einem Ort">
              <p>Die Kinder-Detailansicht zeigt die persönlichen BuDo-Daten, Gesundheitsinformationen, Familiendaten, Schwerpunkt- und Happy-Cleaning-Einteilungen übersichtlich an. Dort findest du außerdem alle Notizen und kannst neue Notizen inklusive Bildern hinzufügen.</p>
              <p>Die Aktivitätskarten für Notizen, <AppLink href="#erste-hilfe">Erste Hilfe</AppLink> und <AppLink href="#taschengeld">Taschengeld</AppLink> lassen sich einzeln öffnen. Die beiden besonders wichtigen Funktionen werden in eigenen Abschnitten erklärt.</p>
            </Subsection>
            <Screenshot src={kidScreenshot} alt="Kinder-Detailansicht für den vollständig synthetischen Eintrag Harry Potter mit BuDo-, Gesundheits-, Familien- und Aktivitätskarten" caption="Kinder-Detailansicht: Stammdaten, Gesundheit, BuDo-Einteilungen, Notizen, Erste Hilfe und Taschengeld." />
            <Subsection title="Daten bearbeiten">
              <p>Über <strong>Bearbeiten</strong> rechts oben können Orgis Kinderdaten korrigieren, wenn Eltern beispielsweise falsche Informationen eingegeben haben. Beim Alter wird visuell darauf hingewiesen, wenn Geburtstag und Sozialversicherungsnummer nicht übereinstimmen.</p>
              <p>Beim Check-in kann standardmäßig nach dem Alter gefragt werden. Bei Kindern mit einer Abweichung zwischen Geburtstag und Sozialversicherungsnummer sollte aber auf jeden Fall nachgefragt werden. Fehlt das Einverständnis für ärztliche Behandlung oder ist es unklar, erscheint ebenfalls ein Rufzeichen als visueller Hinweis für ein mögliches Gespräch mit den Eltern.</p>
            </Subsection>
            <Subsection title="Check-in">
              <p>Klicke auf <strong>Einchecken</strong> und trage das Check-in-Datum ein – normalerweise ist das das aktuelle Datum, bei Bedarf kann aber ein anderes gewählt werden. Danach markierst du, ob Ausweis, E-Card und Einverständniserklärung übernommen wurden.</p>
              <p>Beim Check-in kannst du direkt eine Notiz und das eingezahlte Taschengeld erfassen. Wie das Guthaben danach gebucht und kontrolliert wird, steht im Abschnitt <AppLink href="#taschengeld">Taschengeld</AppLink>.</p>
            </Subsection>
          </Section>

          <Section id="taschengeld" number="7" title="Taschengeld" audience="Für Betreuer:innen und Orgis">
            <p>Das beim Check-in eingezahlte Taschengeld wird direkt beim Kind erfasst. Dadurch steht von Anfang an ein nachvollziehbarer Kontostand zur Verfügung und die Orgi-Übersicht kann den erwarteten Kassenstand berechnen.</p>
            <Subsection title="Beim Kind buchen">
              <p>In der Kinder-Detailansicht kannst du in der Taschengeld-Karte Pfand erhöhen oder verringern, Geld abbuchen oder aufladen und die gesamte Transaktionsgeschichte des Kindes sehen. Der aktuelle Betrag steht direkt im Kartentitel; bei weniger als fünf Euro weist ein Warnsymbol auf das niedrige Guthaben hin.</p>
              <p>Besonders praktisch bei der Taschengeldausgabe: Nachdem du bei einem Kind eine Buchung gemacht hast, suchst du über die globale Suche das nächste Kind. Beim Öffnen erscheint dieselbe Ansicht mit der Taschengeld-Karte bereits geöffnet. Die Sidebar kann dabei eingeklappt bleiben, damit mehr Platz für die Karten zur Verfügung steht.</p>
            </Subsection>
            <Screenshot src={kidMoneyScreenshot} alt="Kinder-Detailansicht des vollständig synthetischen Kindes Harry Potter mit eingeklappter Sidebar und geöffneter Taschengeld-Karte samt Pfand, Buchungsformular und Transaktionen" caption="Taschengeld beim Kind: eingeklappte Sidebar, geöffnete Karte, Pfand, aktuelles Guthaben und Transaktionsgeschichte." />
            <Subsection title="Orgi-Übersicht und Kassenabgleich">
              <p>Unter <AppLink href="/taschengeld/">Orgi › Taschengeld</AppLink> stehen alle getätigten Transaktionen mit Betrag, Kind und der Person, die sie durchgeführt hat. Außerdem zeigt die Seite, wie viel Bargeld sich rechnerisch gerade in der Kasse befinden sollte. Dieser erwartete Kassenstand wird am Turnusende mit dem tatsächlichen Bestand abgeglichen.</p>
            </Subsection>
            <Screenshot src={pocketScreenshot} alt="Orgi-Taschengeldübersicht mit ausschließlich synthetischen Transaktionen von Harry Potter, Hermione Granger, Neville Longbottom und Ginny Weasley" caption="Taschengeldübersicht für Orgis: Einzahlungen, Ausgaben, erwarteter Kassenstand und verantwortliche Person." />
          </Section>

          <Section id="schwerpunkte" number="8" title="Schwerpunkte" audience="Planung durch Team & Orgi">
            <p>Die Schwerpunkte können dem Orga-Team extrem viel Arbeit abnehmen und machen die Einteilung für Betreuer:innen leichter und übersichtlicher. Unter <AppLink href="/swp-einteilung-w1">SWP 1</AppLink> beziehungsweise <AppLink href="/swp-einteilung-w2">SWP 2</AppLink> können Betreuer:innen ihre Schwerpunkte hinzufügen und angeben, wie der Schwerpunkt heißt, was ungefähr gemacht wird und wohin ausgelagert wird.</p>
            <Subsection title="Wünsche erfassen und Kinder einteilen">
              <p>Wenn die Schwerpunktpräsentation vorbei ist und alle Zettel vorliegen, werden die Kinder direkt eingeteilt. In die Kinder-Filterleiste gibst du den Namen eines Kindes ein, findest dadurch die richtige Zeile und trägst 1., 2. und 3. Wahl sowie gewünschte Freund:innen ein. Danach ist automatisch die erste Wahl als Einteilung ausgewählt und kann bei Bedarf geändert werden.</p>
            </Subsection>
            <Subsection title="Einteilung ausbalancieren">
              <p>Oben in der Übersicht steht, wie viele Kinder pro Schwerpunkt eingeteilt sind, wie das Geschlechterverhältnis und das Verhältnis der BuDo-Familien aussehen und wie hoch das Durchschnittsalter ist. Über <strong>Kinder anzeigen</strong> beziehungsweise <strong>Kinder ausblenden</strong> lässt sich die komplette Kinderliste der Schwerpunkte ein- und ausblenden. Die Schwerpunktlisten sind druckbar.</p>
            </Subsection>
            <Screenshot src={allocationScreenshot} alt="Schwerpunkt-Einteilung mit den synthetischen Schwerpunkten Quidditch, Zauberkunst und Phantastische Tierwesen sowie Harry-Potter-Beispielkindern" caption="Schwerpunktübersicht mit Statistik, Kinderfilter, Wahlen und Freund:innenwünschen." />
            <Subsection title="Schwerpunkt-Detailansicht und Essen">
              <p>Ein Klick auf den Namen eines Schwerpunkts öffnet seine Detailansicht. Die umfangreichere Tabelle enthält Familie, Geschlecht, Alter, Ernährung, Medikamente und gesundheitliche Informationen. Auch Geburtstage werden angezeigt. Dadurch können sich Betreuer:innen schnell und unkompliziert einen Überblick verschaffen, ob es etwas Wichtiges zu wissen gibt.</p>
              <p>In der Detailansicht kann das Essen für Betreuer:innen angegeben werden: im BuDo essen, warmes Essen geliefert bekommen oder eine Lunchbox mitnehmen. Diese Angaben laufen in der Küchenübersicht zusammen.</p>
            </Subsection>
          </Section>

          <Section id="happy-cleaning" number="9" title="Happy Cleaning" audience="Gemeinsame Einteilung im Team">
            <p>Happy Cleaning erlaubt es, alle Kinder einzuteilen. Das Coole daran ist, dass mehrere Betreuer:innen parallel arbeiten können.</p>
            <Callout title="Empfehlung für die Einteilung">
              <p>Stellt im Essensbereich mehrere Tische an der Wand bei den Getränkespendern auf und setzt drei Personen mit Laptops dorthin. So können drei Personen gleichzeitig Kinder suchen, Nummern erfassen und Stationen zuweisen.</p>
            </Callout>
            <Subsection title="Stationen vorbereiten">
              <p>Stationen können beispielsweise „Große Halle“, „Essensbereich“ oder eine andere Happy-Cleaning-Station sein. In der Bearbeitung legst du fest, wie viele Kinder maximal dort sein sollen, wo der Treffpunkt ist, wer betreuen kann und welche Kinderwünsche bei der Einteilung berücksichtigt werden sollen.</p>
              <p>Zusätzlich werden die Aufgaben der Station definiert. Dadurch wird nichts vergessen. Diese Checklisten müssen nicht jedes Mal neu geschrieben werden: Stationen können aus anderen Turnussen oder einem früheren Happy Cleaning kopiert und anschließend angepasst werden. So bleiben bestehendes Wissen und sinnvolle Checklisten erhalten.</p>
            </Subsection>
            <Subsection title="Parallel einteilen und Fortschritt sehen">
              <p>Bei der Einteilung können Kindernummern eingetragen und die Kinder Stationen zugewiesen werden. Betreuer:innen sehen ihre Station, die eingeteilten Kinder und die To-do-Liste danach direkt im Dashboard und können Aufgaben abhaken.</p>
              <p>In der Stationseinteilung sieht das Team außerdem, wie weit die Aufgaben an den einzelnen Stationen fortgeschritten sind. Wenn eine Station schon fast fertig ist und eine andere noch wenig geschafft hat, kann man gezielt dort unterstützen. So hat man einen guten Gesamtüberblick darüber, wie weit das Happy Cleaning ist.</p>
            </Subsection>
            <Screenshot src={cleaningScreenshot} alt="Happy-Cleaning-Einteilung mit ausschließlich synthetischen Harry-Potter-Kindern und den Stationen Große Halle, Küche und Eingangsbereich" caption="Happy Cleaning: parallele Kindersuche, Stationskapazitäten, Wünsche, Treffpunkte und Aufgabenfortschritt." />
          </Section>

          <Section id="auslagerorte" number="10" title="Auslagerorte" audience="Wissenssammlung für Team & Orgi">
            <p>Die leidige Suche nach einem Auslagerort: Die Redmap enthält leider oft nur wenige Informationen, teilweise nicht einmal eine Adresse. In BuDoBase gibt es deshalb auf der einen Seite eine Karte und auf der anderen Seite eine laufend wachsende Wissenssammlung.</p>
            <p>Auf der Karte findest du Auslagerorte und weitere Orte, die im BuDo-Alltag gut zu wissen sind. Dazu können beispielsweise Orte gehören, die vor allem für Organisator:innen wichtig sind. Gerade neue Orgis können so unkompliziert zum richtigen Ort navigieren.</p>
            <Subsection title="Orte ergänzen und Wissen teilen">
              <p>Betreuer:innen können Auslagerorte hinzufügen; Orgis können außerdem relevante Alltagsorte ergänzen. Tags helfen beim Filtern und sorgen für passende Symbole auf der Karte. Bei jedem Ort lassen sich Bilder und Kommentare hinzufügen.</p>
              <p>Bitte macht von dieser Funktion tatsächlich Gebrauch. Je mehr Erfahrungen, Hinweise und Fotos zusammenkommen, desto schneller lässt sich entscheiden, welcher Auslagerort spannend und geeignet ist. So können auch neue Orte ausprobiert werden, statt immer nur zu denselben drei Auslagerorten zu fahren.</p>
            </Subsection>
            <Screenshot src={placesScreenshot} alt="Auslagerorte-Seite mit synthetischer Karte und dem erfundenen Eintrag Verbotener Wald samt Tags, Beschreibung, Kontakt, Adresse und Kommentarformular" caption="Auslagerorte verbinden Karte, Filter, Navigation, Bilder, Kommentare und Erfahrungswissen." />
          </Section>

          <Section id="spiele" number="11" title="Spiele" audience="Für Betreuer:innen">
            <p><strong>Spiele</strong> ist ein externer Link zu Daniels Spieledatenbank. Sie ist besonders hilfreich bei der Planung von Familienprogrammen. Dort ist ein Haufen Spiele erklärt – unter anderem viele Kennenlernspiele.</p>
          </Section>

          <Section id="team-turnus" number="12" title="Team & Turnus" audience="Für alle; Verwaltung durch Leitung & Orgi">
            <p><AppLink href="/teams/">Team & Turnus</AppLink> gibt einen Überblick über die verschiedenen Turnusse und darüber, wer im eigenen Turnus arbeitet. Leitungen und Organisator:innen können dort die Kinderliste hochladen und Teampersonen hinzufügen.</p>
            <Subsection title="So kommt das Team in den Turnus">
              <p>Jede Person aus dem Team erstellt zuerst einen eigenen Account. Danach kann sie auf der Seite „Team & Turnus“ eine Anfrage für den Turnus schicken, in dem sie arbeitet. Leitungen oder Organisator:innen prüfen und bestätigen diese Anfrage.</p>
              <p>Personen, die bereits in anderen Turnussen mitgearbeitet haben, können von Leitung oder Orgi auch direkt zum Turnus hinzugefügt werden.</p>
            </Subsection>
          </Section>

          <Section id="kueche" number="13" title="Küche" audience="Für Orgi und Küche">
            <p>Unter <AppLink href="/kitchen">Küche</AppLink> laufen die Essenswünsche aus den Schwerpunkt-Detailansichten zusammen. Der Organisator beziehungsweise die Küche sieht dort, wie viele Portionen für wen gemacht werden müssen – inklusive Allergien und Unverträglichkeiten.</p>
            <p>Damit die Zahlen stimmen, sollten die Betreuenden vor der Küchenplanung vollständig eintragen, ob sie im BuDo essen, warmes Essen geliefert bekommen oder eine Lunchbox möchten.</p>
          </Section>

          <Section id="orgi" number="14" title="Orgi-Funktionen" audience="Für Organisator:innen">
            <p>Die Taschengeld-Funktionen sind wegen ihrer Bedeutung für das gesamte Team in einem eigenen Abschnitt zusammengefasst: <AppLink href="#taschengeld">Taschengeld öffnen</AppLink>.</p>
            <Subsection title="Serienbrief">
              <p>Am Anfang des Turnus kann nach dem Check-in der <AppLink href="/serienbrief">Serienbrief</AppLink> für die Kindermappen gedruckt werden. Er enthält die benötigten Informationen zu E-Card, Ausweis und weiteren Check-in-Daten.</p>
              <p>Der Ausdruck ist inzwischen etwas weniger kritisch, weil diese Informationen bei einer Krankenhausfahrt jederzeit digital gesichert abrufbar sind. Als geordnete Papierunterlage kann der Serienbrief trotzdem hilfreich sein.</p>
            </Subsection>
            <Subsection title="Aufenthaltsdokumentation">
              <p>Der wahrscheinlich wichtigste Button für den Orgi ist <strong>Aufenthaltsdoku</strong>. Am Ende des Turnus genügt ein Klick, und eine Datei mit der fertigen Aufenthaltsdokumentation wird heruntergeladen.</p>
              <p>BuDoBase vergleicht dafür die ursprünglichen Angaben aus dem Excel-Kinderlisten-File mit den tatsächlich erfassten Daten zur Zuganreise, Zugabreise und zu vorzeitigen Abreisen. So wird sichtbar, ob sich zwischen Anmeldung und tatsächlicher Mitfahrt oder Anwesenheit etwas verändert hat.</p>
              <p>In der Datei steht, welche Kinder in der ersten und zweiten Woche anwesend waren, die Zugan- oder Zugabreise in Anspruch genommen haben oder vorzeitig abgereist sind. Die Informationen, die Stefan braucht, sind dadurch automatisch gesammelt.</p>
            </Subsection>
          </Section>

          <Section id="abschluss" number="15" title="Am Ende des Turnus" audience="Checkliste für das Orga-Team">
            <ol className="grid list-decimal gap-3 pl-6">
              <li>Prüfen, ob Zuganreise, Zugabreise und vorzeitige Abreisen vollständig erfasst sind.</li>
              <li>Die Aufenthaltsdokumentation über <strong>Aufenthaltsdoku</strong> herunterladen und inhaltlich kontrollieren.</li>
              <li>Wenn die digitale Erste Hilfe genutzt wurde, die vollständige EH-Dokumentation drucken oder als PDF speichern und Stefan übergeben.</li>
              <li>Den erwarteten Taschengeld-Kassenstand mit dem tatsächlichen Bestand abgleichen.</li>
              <li>Sinnvolle Happy-Cleaning-Checklisten sowie neue Erfahrungen und Bilder zu Auslagerorten für kommende Turnusse erhalten.</li>
            </ol>
            <Callout title="Kurz gesagt">
              <p>BuDoBase soll Informationen dort sammeln, wo sie gebraucht werden: beim Kind, beim Schwerpunkt, bei der Station, beim Auslagerort und am Ende automatisch in den notwendigen Dokumenten. Je konsequenter das ganze Team dieselben Funktionen nutzt, desto weniger Wissen geht verloren und desto weniger Papierlisten müssen parallel gepflegt werden.</p>
            </Callout>
          </Section>
        </article>
      </div>
    </main>
  );
}

export const documentationRoutes = [{
  pattern: /^\/dokumentation$/,
  page: 'documentation',
  title: 'Dokumentation',
  domain: 'documentation',
  readContractKey: 'documentation',
  headerAction: () => (
    <Button
      aria-label="Dokumentation drucken"
      className="mobile-icon-action"
      size="responsive-icon"
      type="button"
      onClick={() => window.print()}
    >
      <span className="desktop-action-label">Drucken</span>
      <Printer className="mobile-action-label" aria-hidden="true" />
    </Button>
  ),
  render: () => <DocumentationPage />,
}];
