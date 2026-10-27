# Financial Risk-tema

`financial-risk.json` är ett återanvändbart Power BI-tema. Det använder projektets Navy `#182B42`, Blue `#316B9B`, Risk Orange `#D38B52`, Background `#F3F6FA` och Muted text `#64748B`. Temats färger anger standardvärden; explicit formatering i en visual kan överstyra dem.

## Befintliga segmentfärger

Den befintliga stapelvisualen har explicita datapunktsfärger för Prime (`#182B42`) och Subprime (`#D38B52`), samt blå standardfärg (`#316B9B`) för övriga segment, däribland Near-prime. Visualens definition har inte ändrats. Temats `dataColors` är en palett och kopplar inte färg permanent till segmentnamn. Kontrollera därför segmentfärgerna visuellt efter import, inklusive vid filtrering och sortering.

## Importera och kontrollera i arbetskopian

1. Öppna `../CreditRisk.pbip` i Power BI Desktop. Om arbetskopian redan är öppen, spara först ditt aktuella arbete.
2. Välj **Visa** eller **Design** > **Teman** > **Bläddra efter teman / Importera tema** (menyerna kan variera mellan Desktop-versioner).
3. Välj `financial-risk.json` i denna mapp. Spara endast arbetskopian när import och visuell kontroll lyckats.
4. Bekräfta att temat accepteras och att segmentdiagrammet visar Prime navy, Near-prime blå och Subprime orange. Kontrollera även kort, diagram, bakgrund och läsbarhet; befintliga lokala formateringar kan överstyra temats standardvärden.
5. Kontrollera att samma KPI-värden och filter visas som före importen.

Import och sparande i Desktop uppdaterar rapportens PBIR-temareferenser och registrerar normalt en temaresurs i rapportmappen. Utvärdera de faktiska ändringarna efter import. Ingen rapportdefinition ändrades när denna temafil skapades. En eventuell omställning av specifika visualer eller deras explicita färger kräver ett separat beslut.

## Ändringsförteckning

- Ny `powerbi/themes/financial-risk.json`: Power BI-tema.
- Ny `powerbi/themes/README.md`: användning och begränsningar.

Inga befintliga rapport-, modell- eller datafiler ändrades vid detta steg. JSON och dess använda egenskaper kontrolleras lokalt mot Microsofts temaschema. Import i Power BI Desktop och visuell kontroll har inte utförts av assistenten.
