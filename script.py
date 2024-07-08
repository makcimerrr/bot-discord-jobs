import os
import discord
import json
import requests
import asyncio
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from dotenv import load_dotenv  # Import dotenv module

# Load environment variables from .env file
load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


def fetch_new_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    querystring = {
        "query": "Developer fullstack in france",
        "page": "1",
        "num_pages": "1",
        "date_posted": "all",
        "employment_types": "INTERN"
    }
    headers = {
        "x-rapidapi-key": "a8fbf570efmsh8342bf88927fc47p1a79c7jsn755be17fe9ae",
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json()
        jobs = data.get('data', [])
        return jobs if isinstance(jobs, list) else []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching jobs from new API: {e}")
        return []


# Fonction pour obtenir les offres d'emploi depuis l'API LinkedIn Jobs Search
def fetch_linkedin_jobs():
    url = "https://linkedin-jobs-search.p.rapidapi.com/"
    payload = {
        "search_terms": "Alternance_Développeur",
        "location": "Rouen, France",
        "page": "1",
        "employment_type": ["INTERN"]
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": "a8fbf570efmsh8342bf88927fc47p1a79c7jsn755be17fe9ae",
        "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com"
    }

    response = requests.post(url, json=payload, headers=headers)
    jobs = response.json()

    return jobs


# Fonction pour obtenir les offres d'emploi depuis l'API Indeed
def fetch_indeed_jobs():
    url = "https://indeed12.p.rapidapi.com/jobs/search"
    querystring = {
        "query": "alternant développeur",
        "location": "rouen",
        "page_id": "1",
        "locality": "fr",
        "fromage": "1",
        "radius": "50",
        "sort": "date"
    }
    headers = {
        "x-rapidapi-key": "9ebfc16424msh31785378b8b5536p1d17d6jsncc048dd648a3",
        "x-rapidapi-host": "indeed12.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        jobs = response.json().get('hits', [])
        return jobs if isinstance(jobs, list) else []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Indeed jobs: {e}")
        return []


async def send_joblist(ctx=None):
    forum_channel_id = 1245322710825832502  # ID du canal ForumChannel
    forum_channel = bot.get_channel(forum_channel_id)

    if isinstance(forum_channel, discord.ForumChannel):
        # Obtenir les threads actifs et archivés existants
        active_threads = forum_channel.threads
        archived_threads = [
            thread
            async for thread in forum_channel.archived_threads(limit=100)
        ]

        all_threads = active_threads + archived_threads

        # Récupérer les offres d'emploi depuis les API
        linkedin_jobs = fetch_linkedin_jobs()
        indeed_jobs = fetch_indeed_jobs()
        jSearch_jobs = fetch_new_jobs()

        # Fusionner les deux listes d'offres d'emploi
        all_jobs = linkedin_jobs + indeed_jobs

        all_new_jobs = jSearch_jobs

        for job in all_new_jobs:
            company = job.get('employer_name')
            title = job.get('job_title')
            link = job.get('job_apply_link')
            date = job.get('job_posted_at_datetime_utc')
            technologies = job.get('job_required_skills', 'Non spécifié')

            if title and link and company:
                thread_title = f"{company} - {title}"

                if date and link:
                    thread_content = f"Bonjour <@&1245022493371011135> ! Offre d'alternance chez **{company}** qui recherche un développeur **{title}** utilisant les technologies suivantes : **{technologies}**. Pour plus de détails et pour postuler, cliquez sur le lien : {link}"

                    # Chercher un thread existant avec le même titre
                    existing_thread = None
                    for thread in all_threads:
                        if thread.name == thread_title:
                            existing_thread = thread
                            break

                    # Si un thread avec le même titre existe déjà, passe au suivant
                    if existing_thread:
                        print("Thread found:", existing_thread.name)
                        continue

                    # Créer le nouveau thread
                    try:
                        thread = await forum_channel.create_thread(
                            name=thread_title, content=thread_content)
                    except discord.errors.HTTPException as e:
                        if e.code == 429:
                            print(
                                "Rate limited by Discord, will try again later."
                            )
                            break

                    # Pause pour éviter de dépasser les limites de taux
                    await asyncio.sleep(1)

                if ctx:
                    await ctx.send("Les offres d'emploi ont été mises à jour.")
            else:
                print("Le canal spécifié n'est pas un ForumChannel.")
                if ctx:
                    await ctx.send(
                        "Le canal spécifié n'est pas un ForumChannel.")

        for job in all_jobs:
            title = job.get("job_title") or job.get("title")
            company = job.get("company_name")
            date = job.get("posted_date") or job.get("formatted_relative_time")
            link = job.get("linkedin_job_url_cleaned"
                           ) or "https://fr.indeed.com" + job.get("link")
            technologies = job.get('skills', 'Non spécifié')
            if title and link and company:
                thread_title = f"{company} - {title}"

                if date and link:
                    thread_content = f"Bonjour <@&1245022493371011135> ! Offre d'alternance chez **{company}** qui recherche un développeur **{title}** utilisant les technologies suivantes : **{technologies}**. Pour plus de détails et pour postuler, cliquez sur le lien : {link}"

                    # Chercher un thread existant avec le même titre
                    existing_thread = None
                    for thread in all_threads:
                        if thread.name == thread_title:
                            existing_thread = thread
                            break

                    # Si un thread avec le même titre existe déjà, passe au suivant
                    if existing_thread:
                        print("Thread found:", existing_thread.name)
                        continue

                    # Créer le nouveau thread
                    try:
                        thread = await forum_channel.create_thread(
                            name=thread_title, content=thread_content)
                    except discord.errors.HTTPException as e:
                        if e.code == 429:
                            print(
                                "Rate limited by Discord, will try again later."
                            )
                            break

                    # Pause pour éviter de dépasser les limites de taux
                    await asyncio.sleep(1)
        if ctx:
            await ctx.send("Les offres d'emploi ont été mises à jour.")
    else:
        print("Le canal spécifié n'est pas un ForumChannel.")
        if ctx:
            await ctx.send("Le canal spécifié n'est pas un ForumChannel.")


@bot.event
async def on_ready():
    print('Bot is ready.')
    # Démarrage du scheduler pour exécuter la fonction send_joblist deux fois par jour
    scheduler.start()


# Scheduler pour exécuter la fonction send_joblist deux fois par jour
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=10, minute=0)  # Exécuter à 8h du matin
async def joblist_morning():
    await send_joblist()


@scheduler.scheduled_job("cron", hour=18, minute=0)  # Exécuter à 16h
async def joblist_evening():
    await send_joblist()


@bot.command(name='update_jobs')
async def update_jobs(ctx):
    await send_joblist()

# ID du rôle autorisé
ALLOWED_ROLE_ID = 1245022469719457812  # Remplace par l'ID de ton rôle

# Description par défaut de l'embed
DEFAULT_EMBED_DESCRIPTION = "Description par défaut de l'embed."

last_embed_message_id = {}
@bot.command(name='sendembed')
async def send_embed(ctx, channel: discord.TextChannel, new_description: str = None):
    # Vérifie si l'utilisateur a le rôle autorisé
    role = discord.utils.get(ctx.guild.roles, id=ALLOWED_ROLE_ID)
    if role not in ctx.author.roles:
        await ctx.send("Vous n'avez pas la permission d'utiliser cette commande.")
        return

    # Créer l'embed avec la description par défaut ou la nouvelle description si fournie
    if new_description:
        embed_description = new_description
    else:
        embed_description = DEFAULT_EMBED_DESCRIPTION

    embed = discord.Embed(title="Besoin d'aide ?",
                          description="Pour demander de l'aide auprès d'autres apprenants de ta promo, clique sur le bouton ci-dessous\n\n> Une fois ta demande effectuée, tu te verras attribuer un rôle et un pseudo. Des apprenants viendront sous peu t'apporter de l'aide !",
                          colour=0x002e7a,
                          timestamp=datetime.now())

    embed.set_author(name="Info")

    embed.set_footer(text="Zone01",
                     icon_url="https://zone01rouennormandie.org/wp-content/uploads/2024/03/01talent-profil-400x400-1.jpg")

    # Vérifie s'il existe déjà un embed dans le salon spécifié
    if channel.id in last_embed_message_id:
        try:
            # Récupère le message en utilisant l'ID stocké et le met à jour avec le nouvel embed et le bouton
            message = await channel.fetch_message(last_embed_message_id[channel.id])
            await message.edit(embed=embed)
            await ctx.send(f"Embed mis à jour dans {channel.mention}")
        except discord.NotFound:
            # Message non trouvé, envoie un nouvel embed avec le bouton et met à jour l'ID stocké
            message = await channel.send(embed=embed)
            last_embed_message_id[channel.id] = message.id
            await ctx.send(f"Nouvel embed envoyé à {channel.mention}")
    else:
        # Aucun embed précédent trouvé, envoie un nouveau avec le bouton et stocke son ID
        message = await channel.send(embed=embed)
        last_embed_message_id[channel.id] = message.id
        await ctx.send(f"Nouvel embed envoyé à {channel.mention}")

    await message.add_reaction("🆘")

# Commande pour obtenir l'ID du salon mentionné
@send_embed.error
async def send_embed_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("Veuillez mentionner le salon où envoyer l'embed. Exemple : `!sendembed #nom-du-salon [Nouvelle description de l'embed]`")

## BOT AIDE POUR LES APPRENANTS


# Remplacez selon le message et le rôle à donner pour les aides !
# MESSAGE_ID = 1256205265401937960  # ID du message à surveiller
ROLE_ID = 1245022484902707243  # Remplacez par l'ID du rôle à attribuer
HELP_CHANNEL_ID = 1245022636367675517

ROLE_1 = 1245022492230156381  # P1 2023
ROLE_2 = 1245022493371011135  # P2 2023
ROLE_3 = 1245022489835339859  # P1 2024
@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return  # Si c'est le bot qui a réagi, ne rien faire

    if payload.message_id == last_embed_message_id[payload.channel_id]:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(payload.user_id)

        if member and role:
            channel = bot.get_channel(payload.channel_id)
            message = await channel.fetch_message(payload.message_id)

            if payload.emoji.name == "🆘":
                await member.add_roles(role)
                # Modifier le pseudo de l'utilisateur
                new_nickname = f"🚨 {member.display_name}"
                try:
                    await member.edit(nick=new_nickname)
                except discord.Forbidden:
                    print(f"Je n'ai pas la permission de changer le pseudo de {member}.")

                if member:
                    # Vérifier si le membre possède le rôle spécifique
                    has_role_1 = any(role.id == ROLE_1 for role in member.roles)
                    has_role_2 = any(role.id == ROLE_2 for role in member.roles)
                    has_role_3 = any(role.id == ROLE_3 for role in member.roles)

                    # Déterminer dans quel canal envoyer le message en fonction de la possession du rôle
                    if has_role_1:
                        help_channel_id = 1245022642109419585  # ID du canal P1 2023
                    elif has_role_2:
                        help_channel_id = 1245022643590266950  # ID du canal P2 2023
                    elif has_role_3:
                        help_channel_id = 1245022648577163387  # ID du canal P1 2024
                    else:
                        help_channel_id = 1245022628658548778  # ID du canal par défaut

                    help_channel = bot.get_channel(help_channel_id)
                    if help_channel:
                        await help_channel.send(f"<@{member.id}> a besoin d'aide.")
                    else:
                        print(f"Le canal d'ID {help_channel_id} n'a pas été trouvé.")


@bot.event
async def on_raw_reaction_remove(payload):
    if payload.user_id == bot.user.id:
        return  # Si c'est le bot qui a retiré la réaction, ne rien faire

    if payload.message_id == last_embed_message_id[payload.channel_id]:
        guild = bot.get_guild(payload.guild_id)
        role = guild.get_role(ROLE_ID)
        member = guild.get_member(payload.user_id)

        if member and role:
            await member.remove_roles(role)
            # Restaurer le pseudo d'origine de l'utilisateur
            if member.display_name.startswith("🚨"):
                original_nickname = member.display_name.replace("🚨 ", "")
                try:
                    await member.edit(nick=original_nickname)
                except discord.Forbidden:
                    print(f"Je n'ai pas la permission de changer le pseudo de {member}.")

                if member:
                    # Vérifier si le membre possède le rôle spécifique
                    has_role_1 = any(role.id == ROLE_1 for role in member.roles)
                    has_role_2 = any(role.id == ROLE_2 for role in member.roles)
                    has_role_3 = any(role.id == ROLE_3 for role in member.roles)

                    # Déterminer dans quel canal envoyer le message en fonction de la possession du rôle
                    if has_role_1:
                        help_channel_id = 1245022642109419585  # ID du canal P1 2023
                    elif has_role_2:
                        help_channel_id = 1245022643590266950  # ID du canal P2 2023
                    elif has_role_3:
                        help_channel_id = 1245022648577163387  # ID du canal P1 2024
                    else:
                        help_channel_id = 1245022628658548778  # ID du canal par défaut

                    help_channel = bot.get_channel(help_channel_id)
                    if help_channel:
                        async for message in help_channel.history(limit=None):
                            if f"<@{member.id}> a besoin d'aide." in message.content:
                                await message.delete()
                                break
                    else:
                        print(f"Le canal d'ID {help_channel_id} n'a pas été trouvé.")



        
token = os.getenv('TOKEN')
bot.run(token)
