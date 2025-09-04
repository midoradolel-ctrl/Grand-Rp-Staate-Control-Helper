import discord
from discord import app_commands
from discord.ui import View, Button, Select, Modal, TextInput
from discord import Interaction
import asyncio
import json
import os
from datetime import datetime
import io

# TOKEN HIER EINFÜGEN: Ersetze den Text zwischen den Anführungszeichen mit deinem echten Bot-Token
BOT_TOKEN = "BotTokenHier"

# CHANNEL ID HIER EINFÜGEN: Ersetze mit der ID deines gewünschten Channels
TARGET_CHANNEL_ID = 1412638870532526133

# Bot mit Berechtigungen initialisieren
intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

# Dictionary mit Objekten und ihren Werten
OBJECTS = {
    "RP Fabrik": "2 Tickets",
    "Gießerei": "5 Platten, 5 Revolver, 50 Revolverschuss, 5 Sturmgewehr, 300 Sturmgewehr Schuss, 2 Auto Schrotflinten, 50 Schrotflintenschuss",
    "Ölfelder": "10 Benzin, 10 Diesel, 10 Kerosin",
    "Elektriker": "2 Kabel",
    "Fischerei 1": "5 Barsch, 5 Karpfen, 5 Forelle, 5 Lachs",
    "Fischerei 2": "5 Barsch, 5 Karpfen, 5 Forelle, 5 Lachs",
    "Funkturm": "20 Familienpunkte",
    "Cannabisfarm": "10 Cannabis",
    "Weinberge": "5 Atk Juice, 5 Def Juice",
    "Army base": "5 Revolver, 50 Revolverschuss, 5 Sturmgewehr, 300 Sturmgewehr Schuss, 2 Auto Schrotflinten, 50 Schrotflintenschuss",
    "Gefängnis": "Haftzeit verkürzt",
    "Windpark": "3 Batterien",
    "Steinbruch": "25 Kupfer, 5 Emerald, 3 Rubin, 1 Diamant",
    "Human Labs": "10 Medikits",
    "Farm 1": "10 Kohl, 10 Karpfen, 10 Mandarinen, 10 Ananas",
    "Farm 2": "10 Kohl, 10 Karpfen, 10 Mandarinen, 10 Ananas",
    "Holzfäller": "5 Holz",
    "Waffenfabrik": "5 Revolver, 50 Revolverschuss, 5 Sturmgewehr, 300 Sturmgewehr Schuss, 2 Auto Schrotflinten, 50 Schrotflintenschuss",
    "Tierpark": "Tier Geschenk (Jede Stunde 10% Chance)",
    "Casino": "20.000$"
}

# Globale Zählvariable für jedes Objekt
object_counts = {obj: 0 for obj in OBJECTS.keys()}
hourly_revenue = 0  # Stündlicher Umsatz

# Nachrichten-IDs für spätere Updates
control_message_id = None
saved_files = {}  # Dictionary für gespeicherte Dateien: {filename: message_id}

# Funktion zum Formatieren von Zahlen mit Punkten als Tausendertrennzeichen
def format_currency(amount):
    return f"{amount:,}$".replace(",", ".")

# Funktion zum Erstellen des Embeds mit aktuellen Werten
def create_state_embed():
    embed = discord.Embed(
        title="🔧 State Control",
        description="**Aktuelle State Controls im besitz:**",
        color=0x800080  # Lila Farbe für den Embed-Balken
    )
    
    # Füge für jedes Objekt den Namen und Wert hinzu (inklusive Casino)
    for obj, count in object_counts.items():
        if count > 0:
            value = OBJECTS[obj]
            embed.add_field(
                name=f"{obj}",
                value=value,
                inline=False
            )
    
    # Füge Trennlinie hinzu
    embed.add_field(
        name="--------------------------------------",
        value="",
        inline=False
    )
    
    # Füge stündlichen Umsatz hinzu, falls vorhanden
    total_revenue = hourly_revenue
    if object_counts.get("Casino", 0) > 0:
        total_revenue += 20000  # Casino adds 20.000$
    
    if total_revenue > 0:
        embed.add_field(
            name="**Aktueller Stündlicher Umsatz:**",
            value=f"💰 {format_currency(total_revenue)}",
            inline=False
        )
    
    # Zeige nur das Datum der letzten Sicherung (wenn vorhanden) ganz unten
    if saved_files:
        # Sortiere die Dateien nach Zeitpunkt (neueste zuerst)
        sorted_files = sorted(saved_files.keys(), reverse=True)
        latest_file = sorted_files[0]
        
        # Extrahiere das Datum aus dem Dateinamen
        # Dateiname: state_control_YYYYMMDD_HHMMSS.json
        timestamp = latest_file.replace("state_control_", "").replace(".json", "")
        date_part = timestamp.split("_")[0]
        
        # Formatieren: YYYYMMDD -> DD.MM (nur Tag und Monat)
        formatted_date = f"{date_part[6:8]}.{date_part[4:6]}"
        
        # Füge das Datum ganz unten im Footer hinzu
        embed.set_footer(text=f"Safe file: {formatted_date}")
    
    # Falls keine Objekte vorhanden sind
    if not any(object_counts.values()) and total_revenue == 0:
        embed.add_field(
            name="Keine Objekte",
            value="Noch keine State Control Objekte hinzugefügt",
            inline=False
        )
    
    return embed

# Modal für individuelle Betragseingabe
class RevenueModal(Modal, title="Stündlichen Umsatz anpassen"):
    def __init__(self, operation="add"):
        super().__init__(title="Umsatz anpassen")
        self.operation = operation
        
        self.amount = TextInput(
            label="Betrag eingeben (100$ - 5.000$)",
            placeholder="Gib einen Betrag zwischen 100 und 5000 ein",
            min_length=3,
            max_length=4,
            required=True
        )
        self.add_item(self.amount)
    
    async def on_submit(self, interaction: Interaction):
        global hourly_revenue
        try:
            amount = int(self.amount.value)
            if amount < 100:
                await interaction.response.send_message("❌ Der Betrag muss mindestens 100$ sein!", ephemeral=True, delete_after=3)
                return
            if amount > 5000:
                await interaction.response.send_message("❌ Der Betrag darf maximal 5.000$ sein!", ephemeral=True, delete_after=3)
                return
            
            if self.operation == "add":
                hourly_revenue += amount
                message = f"✅ **{format_currency(amount)}** zum stündlichen Umsatz hinzugefügt!"
            else:
                hourly_revenue = max(0, hourly_revenue - amount)
                message = f"✅ **{format_currency(amount)}** vom stündlichen Umsatz abgezogen!"
            
            # Automatisch das Embed updaten
            await update_embed()
            
            await interaction.response.send_message(message, ephemeral=True, delete_after=3)
            
        except ValueError:
            await interaction.response.send_message("❌ Bitte gib eine gültige Zahl ein!", ephemeral=True, delete_after=3)

# Funktion zum Aktualisieren des Embeds
async def update_embed():
    global control_message_id
    if control_message_id:
        try:
            channel = bot.get_channel(TARGET_CHANNEL_ID)
            if channel:
                message = await channel.fetch_message(control_message_id)
                new_embed = create_state_embed()
                await message.edit(embed=new_embed)
        except Exception as e:
            print(f"❌ Fehler beim automatischen Update des Embeds: {e}")

# Funktion zum Speichern des Zustands als Dateianhang im Channel
async def save_state_to_channel():
    global saved_files
    
    # Daten vorbereiten
    data = {
        "object_counts": object_counts,
        "hourly_revenue": hourly_revenue,
        "saved_at": datetime.now().isoformat()
    }
    
    # JSON-String erstellen
    json_data = json.dumps(data, indent=4)
    
    # Dateinamen erstellen
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"state_control_{timestamp}.json"
    
    # Datei als Bytes-Objekt erstellen
    file_bytes = io.BytesIO(json_data.encode('utf-8'))
    file = discord.File(file_bytes, filename=filename)
    
    try:
        # Datei in den Channel senden
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        message = await channel.send(f"💾 State Control Sicherung: `{filename}`", file=file)
        
        # Nachrichten-ID speichern
        saved_files[filename] = message.id
        
        # Embed aktualisieren
        await update_embed()
        
        return filename
    except Exception as e:
        print(f"❌ Fehler beim Speichern der Datei: {e}")
        return None

# Funktion zum automatischen Speichern um 22:30
async def auto_save_task():
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        now = datetime.now()
        
        # Prüfe ob es 22:30 Uhr ist
        if now.hour == 22 and now.minute == 30:
            filename = await save_state_to_channel()
            if filename:
                print(f"✅ Automatische Sicherung erstellt: {filename}")
                
                # Warte 61 Minuten um sicherzustellen, dass die Aufgabe nur einmal pro Tag ausgeführt wird
                await asyncio.sleep(3660)
            else:
                print("❌ Fehler bei der automatischen Sicherung!")
                await asyncio.sleep(60)  # Warte 1 Minute bei Fehler
        else:
            # Prüfe jede Minute
            await asyncio.sleep(60)

# Funktion zum Laden eines Zustands aus einer Channel-Datei
async def load_state_from_channel(filename, message_id):
    global object_counts, hourly_revenue
    
    try:
        # Nachricht mit der Datei abrufen
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        message = await channel.fetch_message(message_id)
        
        # Anhänge der Nachricht durchsuchen
        for attachment in message.attachments:
            if attachment.filename == filename:
                # Datei herunterladen
                file_content = await attachment.read()
                
                # JSON-Daten parsen
                data = json.loads(file_content.decode('utf-8'))
                
                # Zustand laden
                object_counts = data.get("object_counts", object_counts)
                hourly_revenue = data.get("hourly_revenue", hourly_revenue)
                
                return True
        
        return False
    except Exception as e:
        print(f"❌ Fehler beim Laden der Datei: {e}")
        return False

# Funktion zum Erstellen der Buttons
def create_buttons():
    class ControlView(View):
        def __init__(self):
            super().__init__(timeout=None)
            
            # Plus und Minus Buttons (nur mit Emojis)
            plus_button = Button(style=discord.ButtonStyle.success, emoji="✅", custom_id="add_button")
            minus_button = Button(style=discord.ButtonStyle.danger, emoji="❌", custom_id="remove_button")
            revenue_button = Button(style=discord.ButtonStyle.secondary, emoji="💰", custom_id="revenue_button")
            save_button = Button(style=discord.ButtonStyle.secondary, emoji="💾", custom_id="save_button")
            
            plus_button.callback = self.plus_callback
            minus_button.callback = self.minus_callback
            revenue_button.callback = self.revenue_callback
            save_button.callback = self.save_callback
            
            self.add_item(plus_button)
            self.add_item(minus_button)
            self.add_item(revenue_button)
            self.add_item(save_button)
        
        async def plus_callback(self, interaction: Interaction):
            # Erstelle ein Select mit allen Objekten und Beschreibungen
            object_options = [
                discord.SelectOption(label=obj, description=OBJECTS[obj][:50] + "..." if len(OBJECTS[obj]) > 50 else OBJECTS[obj])
                for obj in OBJECTS.keys()
            ]
            
            # Teile die Optionen in mehrere Select-Menüs auf, falls zu viele
            if len(object_options) > 25:
                # Erste 25 Optionen
                select1 = Select(
                    placeholder="Wähle ein Objekt (1/2)...",
                    options=object_options[:25],
                    custom_id="object_select_1"
                )
                
                # Zweite 25 Optionen
                select2 = Select(
                    placeholder="Wähle ein Objekt (2/2)...",
                    options=object_options[25:],
                    custom_id="object_select_2"
                )
                
                async def select_callback(interaction: Interaction):
                    selected_obj = interaction.data["values"][0]
                    object_counts[selected_obj] += 1
                    
                    await update_embed()
                    
                    await interaction.response.send_message(
                        f"✅ **{selected_obj}** wurde hinzugefügt!", 
                        ephemeral=True, 
                        delete_after=2
                    )
                
                select1.callback = select_callback
                select2.callback = select_callback
                
                view = View()
                view.add_item(select1)
                view.add_item(select2)
                
                await interaction.response.send_message(
                    "📥 **Objekt hinzufügen:** Wähle ein Objekt aus der Liste", 
                    view=view, 
                    ephemeral=True, 
                    delete_after=30
                )
            else:
                # Einzelnes Select-Menü wenn weniger als 25 Optionen
                object_select = Select(
                    placeholder="Wähle ein Objekt...",
                    options=object_options,
                    custom_id="object_select"
                )
                
                async def select_callback(interaction: Interaction):
                    selected_obj = interaction.data["values"][0]
                    object_counts[selected_obj] += 1
                    
                    await update_embed()
                    
                    await interaction.response.send_message(
                        f"✅ **{selected_obj}** wurde hinzugefügt!", 
                        ephemeral=True, 
                        delete_after=2
                    )
                
                object_select.callback = select_callback
                view = View()
                view.add_item(object_select)
                
                await interaction.response.send_message(
                    "📥 **Objekt hinzufügen:** Wähle ein Objekt aus der Liste", 
                    view=view, 
                    ephemeral=True, 
                    delete_after=30
                )
        
        async def minus_callback(self, interaction: Interaction):
            available_objects = [obj for obj, count in object_counts.items() if count > 0]
            
            if not available_objects:
                await interaction.response.send_message("❌ Keine Objekte zum Entfernen verfügbar!", ephemeral=True, delete_after=2)
                return
            
            # Erstelle ein Select mit verfügbaren Objekten und Beschreibungen
            object_options = [
                discord.SelectOption(label=obj, description=OBJECTS[obj][:50] + "..." if len(OBJECTS[obj]) > 50 else OBJECTS[obj])
                for obj in available_objects
            ]
            
            object_select = Select(
                placeholder="Wähle ein Objekt zum Entfernen...",
                options=object_options,
                custom_id="remove_object_select"
            )
            
            async def select_callback(interaction: Interaction):
                selected_obj = interaction.data["values"][0]
                object_counts[selected_obj] = max(0, object_counts[selected_obj] - 1)
                
                await update_embed()
                
                await interaction.response.send_message(
                    f"❌ **{selected_obj}** wurde entfernt!", 
                    ephemeral=True, 
                    delete_after=2
                )
            
            object_select.callback = select_callback
            view = View()
            view.add_item(object_select)
            
            await interaction.response.send_message(
                "📤 **Objekt entfernen:** Wähle ein Objekt zum Entfernen", 
                view=view, 
                ephemeral=True, 
                delete_after=30
            )
        
        async def revenue_callback(self, interaction: Interaction):
            # Öffne direkt das Modal für Geldbetrag
            options = [
                discord.SelectOption(label="Geld hinzufügen", value="add"),
                discord.SelectOption(label="Geld abziehen", value="subtract")
            ]
            
            select = Select(
                placeholder="Wähle eine Aktion...",
                options=options,
                custom_id="revenue_select"
            )
            
            async def select_callback(interaction: Interaction):
                operation = interaction.data["values"][0]
                # Öffne das Modal für individuelle Betragseingabe
                modal = RevenueModal(operation=operation)
                await interaction.response.send_modal(modal)
            
            select.callback = select_callback
            view = View()
            view.add_item(select)
            
            await interaction.response.send_message("💰 **Geldbetrag anpassen:**", view=view, ephemeral=True, delete_after=15)
        
        async def save_callback(self, interaction: Interaction):
            # Menü für Speichern/Laden anzeigen
            options = [
                discord.SelectOption(label="Aktuellen Zustand speichern", value="save", emoji="💾"),
                discord.SelectOption(label="Gespeicherten Zustand laden", value="load", emoji="📂")
            ]
            
            select = Select(
                placeholder="Wähle eine Aktion...",
                options=options,
                custom_id="save_load_select"
            )
            
            async def select_callback(interaction: Interaction):
                action = interaction.data["values"][0]
                
                if action == "save":
                    # Zustand speichern
                    filename = await save_state_to_channel()
                    if filename:
                        await interaction.response.send_message(
                            f"✅ Zustand gespeichert als `{filename}`", 
                            ephemeral=True, 
                            delete_after=5
                        )
                    else:
                        await interaction.response.send_message(
                            "❌ Fehler beim Speichern!", 
                            ephemeral=True, 
                            delete_after=5
                        )
                elif action == "load":
                    # Verfügbare Dateien prüfen
                    if not saved_files:
                        await interaction.response.send_message(
                            "❌ Keine gespeicherten Zustände gefunden!", 
                            ephemeral=True, 
                            delete_after=5
                        )
                        return
                    
                    # Dateiauswahlmenü erstellen
                    file_options = [
                        discord.SelectOption(label=f, value=f)
                        for f in sorted(saved_files.keys(), reverse=True)[:25]  # Nur die neuesten 25 Dateien anzeigen
                    ]
                    
                    file_select = Select(
                        placeholder="Wähle eine Datei zum Laden...",
                        options=file_options,
                        custom_id="file_select"
                    )
                    
                    async def file_select_callback(interaction: Interaction):
                        selected_file = interaction.data["values"][0]
                        message_id = saved_files[selected_file]
                        
                        if await load_state_from_channel(selected_file, message_id):
                            await update_embed()
                            await interaction.response.send_message(
                                f"✅ Zustand aus `{selected_file}` geladen!", 
                                ephemeral=True, 
                                delete_after=5
                            )
                        else:
                            await interaction.response.send_message(
                                f"❌ Fehler beim Laden von `{selected_file}`!", 
                                ephemeral=True, 
                                delete_after=5
                            )
                    
                    file_select.callback = file_select_callback
                    view = View()
                    view.add_item(file_select)
                    
                    await interaction.response.send_message(
                        "📂 **Zustand laden:** Wähle eine gespeicherte Datei", 
                        view=view, 
                        ephemeral=True, 
                        delete_after=30
                    )
            
            select.callback = select_callback
            view = View()
            view.add_item(select)
            
            await interaction.response.send_message(
                "💾 **Speichern/Laden:** Wähle eine Aktion", 
                view=view, 
                ephemeral=True, 
                delete_after=30
            )
    
    return ControlView()

# Slash Command zum manuellen Refreshen (für Notfälle)
@tree.command(name="res", description="Embed manuell aktualisieren (Notfall)")
async def res_command(interaction: Interaction):
    try:
        await update_embed()
        await interaction.response.send_message("✅ Embed wurde manuell aktualisiert!", ephemeral=True, delete_after=3)
    except Exception as e:
        await interaction.response.send_message(f"❌ Fehler beim Aktualisieren: {e}", ephemeral=True, delete_after=5)

# Slash Command zum Auflisten aller gespeicherten Dateien
@tree.command(name="saves", description="Liste aller gespeicherten Zustände anzeigen")
async def saves_command(interaction: Interaction):
    if not saved_files:
        await interaction.response.send_message("❌ Keine gespeicherten Zustände gefunden!", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="💾 Gespeicherte Zustände",
        description="Hier sind alle verfügbaren Sicherungen:",
        color=0x00ff00
    )
    
    for filename in sorted(saved_files.keys(), reverse=True):
        embed.add_field(
            name=filename,
            value="Klicke auf den Dateinamen zum Herunterladen",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Automatisch Embed posten wenn Bot ready ist
@bot.event
async def on_ready():
    print(f'{bot.user} ist online!')
    
    # Starte den automatischen Speicher-Task
    bot.loop.create_task(auto_save_task())
    
    try:
        # Channel finden
        channel = bot.get_channel(TARGET_CHANNEL_ID)
        if channel is None:
            print(f"❌ Channel mit ID {TARGET_CHANNEL_ID} nicht gefunden!")
            return
        
        # Nach gespeicherten Dateien suchen
        global saved_files
        async for message in channel.history(limit=100):
            if message.author == bot.user and message.attachments:
                for attachment in message.attachments:
                    if attachment.filename.startswith("state_control_") and attachment.filename.endswith(".json"):
                        saved_files[attachment.filename] = message.id
        
        print(f"✅ {len(saved_files)} gespeicherte Dateien gefunden")
        
        # Alte Nachrichten des Bots löschen (außer Dateianhängen)
        async for message in channel.history(limit=20):
            if message.author == bot.user and not message.attachments:
                await message.delete()
                await asyncio.sleep(0.5)  # Kurze Pause zwischen Löschvorgängen
        
        # Embed und Buttons erstellen
        embed = create_state_embed()
        view = create_buttons()
        
        # Embed senden und Message ID speichern - OHNE BENACHRICHTIGUNG (silent=True)
        message = await channel.send(embed=embed, view=view, silent=True)
        global control_message_id
        control_message_id = message.id
        
        print(f"✅ Embed wurde in Channel {channel.name} gepostet! (ID: {control_message_id})")
        
    except Exception as e:
        print(f"❌ Fehler beim Senden des Embeds: {e}")
    
    # Slash Commands sync
    try:
        await tree.sync()
        print("Slash Commands wurden synchronisiert!")
    except Exception as e:
        print(f"Fehler beim Synchronisieren: {e}")

# Button-Interaktionen verarbeiten - KORRIGIERTE VERSION
@bot.event
async def on_interaction(interaction: Interaction):
    # Nur für Button-Interaktionen, die noch nicht beantwortet wurden
    if (interaction.type == discord.InteractionType.component and 
        not interaction.response.is_done()):
        
        custom_id = interaction.data.get('custom_id')
        if custom_id in ['add_button', 'remove_button', 'revenue_button', 'save_button']:
            # Ursprüngliche Interaktion bestätigen
            await interaction.response.defer(ephemeral=True, thinking=False)

# Starte den Bot
if __name__ == "__main__":
    if BOT_TOKEN == "DEIN_BOT_TOKEN_HIER" or not BOT_TOKEN:
        print("❌ FEHLER: Du musst dein Bot-Token im Code eintragen!")
        print("1. Gehe zu https://discord.com/developers/applications")
        print("2. Wähle deinen Bot aus")
        print("3. Gehe zum 'Bot' Tab")
        print("4. Kopiere das Token und ersetze 'DEIN_BOT_TOKEN_HIER'")
    else:
        bot.run(BOT_TOKEN)
