import os
import discord
import json
import requests
import asyncio
import json
from discord.ext import commands, tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from dotenv import load_dotenv  # Import dotenv module

# Load environment variables from .env file
load_dotenv()
# load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

# Charger le contenu du fichier JSON
with open('config.json', 'r') as f:
    config = json.load(f)

# Accéder aux variables du fichier JSON
role_ping = config["role_ping"]
forum_channel_id = config["forum_channel_id"]

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.guilds = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)


# Function to fetch jobs from JSearch API
def fetch_new_jobs():
    url = "https://jsearch.p.rapidapi.com/search"
    querystring = {
        "query": "Developer fullstack in rouen, France",
        "page": "1",
        "num_pages": "1",
        "date_posted": "all",
        "employment_types": "INTERN",
        "radius": "120"
    }
    headers = {
        "x-rapidapi-key": os.getenv('RAPIDAPI_KEY'),
        "x-rapidapi-host": "jsearch.p.rapidapi.com"
    }
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        data = response.json().get('data', [])
        return data if isinstance(data, list) else []
    except requests.exceptions.RequestException as e:
        print(f"Error fetching JSearch jobs: {e}")
        return []


# Function to fetch jobs from LinkedIn Jobs Search API
def fetch_linkedin_jobs():
    url = "https://linkedin-jobs-search.p.rapidapi.com/"
    payload = {
        "search_terms": "Alternance_Développeur",
        "location": "Rouen, France",
        "radius": "120",
        "page": "1",
        "employment_type": ["INTERN"]
    }
    headers = {
        "content-type": "application/json",
        "X-RapidAPI-Key": os.getenv('RAPIDAPI_KEY'),
        "X-RapidAPI-Host": "linkedin-jobs-search.p.rapidapi.com"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        response.raise_for_status()

        # Ensure response is parsed as JSON and handle potential list vs dictionary issue
        jobs = response.json()

        if isinstance(jobs, list):
            # Handle list response if necessary
            return jobs
        elif isinstance(jobs, dict):
            # Normal case: extract 'jobs' key from dictionary
            return jobs.get('jobs', [])
        else:
            # Unexpected response type
            print(f"Unexpected response type from LinkedIn API: {type(jobs)}")
            return []

    except requests.exceptions.RequestException as e:
        print(f"Error fetching LinkedIn jobs: {e}")
        return []


# Function to fetch jobs from Indeed API
def fetch_indeed_jobs():
    url = "https://indeed12.p.rapidapi.com/jobs/search"
    querystring = {
        "query": "alternant développeur",
        "location": "rouen",
        "page_id": "1",
        "locality": "fr",
        "fromage": "1",
        "radius": "120",
        "sort": "date"
    }
    headers = {
        "x-rapidapi-key": os.getenv('RAPIDAPI_KEY'),
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


async def send_joblist(ctx=None, loading_message=None):
    global bugs
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
        await asyncio.sleep(1)
        indeed_jobs = fetch_indeed_jobs()
        await asyncio.sleep(1)
        jSearch_jobs = fetch_new_jobs()
        await asyncio.sleep(1)

        verif1 = False
        verif2 = False
        verif3 = False

        if ctx:
            bugs = []
            if not linkedin_jobs:
                # await ctx.send("Erreur lors de la récupération des offres d'emploi depuis LinkedIn.")
                bugs.append("Linkedin")
                verif1 = True
            if not indeed_jobs:
                # await ctx.send("Erreur lors de la récupération des offres d'emploi depuis Indeed.")
                bugs.append("Indeed")
                verif2 = True
            if not jSearch_jobs:
                # await ctx.send("Erreur lors de la récupération des offres d'emploi depuis JSearch.")
                bugs.append("JSearch")
                verif3 = True

            if verif1 and verif2 and verif3:
                if loading_message:
                    # Modifier l'embed de chargement pour indiquer la fin de la mise à jour
                    embed_updated = discord.Embed(
                        title="Erreur lors de la mise à jour",
                        description=f"Aucune des listes d'offres d'emploi n'a pu être mise à jour. Veuillez réessayer plus tard.",
                        color=discord.Color.red()
                    )
                    await loading_message.edit(embed=embed_updated)
                return
            elif verif1 or verif2 or verif3:
                await ctx.send(
                    f"La liste des offres d'emploi de {bugs} n'a pas pu être mise à jour. Veuillez réessayer plus tard.")

        # Fusionner les deux listes d'offres d'emploi
        all_jobs = linkedin_jobs + indeed_jobs

        all_new_jobs = jSearch_jobs

        found_threads_jsearch = []

        for job in all_new_jobs:
            company = job.get('employer_name')
            title = job.get('job_title')
            link = job.get('job_apply_link')
            date = job.get('job_posted_at_datetime_utc')
            technologies = job.get('job_required_skills', 'Non spécifié')
            city = job.get('job_city', 'Non spécifié')

            if title and link and company:
                thread_title = f"{company} - {title}"

                if date and link:
                    thread_content = f"Bonjour <@&{role_ping}> ! Offre d'alternance sur **{city}**, chez **{company}** qui recherche un développeur **{title}** utilisant les technologies suivantes : **{technologies}**. Pour plus de détails et pour postuler, cliquez sur le lien : {link}"

                    # Chercher un thread existant avec le même titre
                    existing_thread = None
                    for thread in all_threads:
                        if thread.name == thread_title:
                            existing_thread = thread
                            found_threads_jsearch.append(existing_thread)
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
                    await asyncio.sleep(1)

        found_threads = []

        for job in all_jobs:
            title = job.get("job_title") or job.get("title")
            company = job.get("company_name")
            date = job.get("posted_date") or job.get("formatted_relative_time")
            link = job.get("linkedin_job_url_cleaned"
                           ) or job.get("indeed_final_url")
            technologies = job.get('skills', 'Non spécifié')
            city = job.get('job_location', 'Non spécifié') or job.get('location', 'Non spécifié')
            if title and link and company:
                thread_title = f"{company} - {title}"

                if date and link:
                    thread_content = f"Bonjour <@&{role_ping}> ! Offre d'alternance sur **{city}**, chez **{company}** qui recherche un développeur **{title}** utilisant les technologies suivantes : **{technologies}**. Pour plus de détails et pour postuler, cliquez sur le lien : {link}"

                    # Chercher un thread existant avec le même titre
                    existing_thread = None
                    for thread in all_threads:
                        if thread.name == thread_title:
                            existing_thread = thread
                            found_threads.append(existing_thread)
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

                    await asyncio.sleep(1)
        if ctx:
            verif = False
            bugs = []
            if len(found_threads) == len(all_jobs):
                # await ctx.send("Les offres d'emploi de LinkedIn et Indeed sont deja à jour.")
                bugs.append("Linkedin")
                bugs.append("Indeed")
                # print(all_jobs)
                verif = True
            if len(found_threads_jsearch) == len(all_new_jobs):
                # await ctx.send("Les offres d'emploi de JSearch sont déjà à jour.")
                bugs.append("JSearch")
                # print(all_new_jobs)
                verif = True

        if loading_message:
            if len(bugs) > 0:
                description = f"Les offres d'emploi de {bugs} sont déjà à jour."
                # Modifier l'embed de chargement pour indiquer la fin de la mise à jour
                embed_updated = discord.Embed(
                    title="Mise à jour terminée",
                    description=description,
                    color=discord.Color.green()
                )
                await loading_message.edit(embed=embed_updated)
            else:
                embed_updated = discord.Embed(
                    title="Mise à jour terminée",
                    description="La liste des offres d'emploi a été mise à jour avec succès.",
                    color=discord.Color.green()
                )
                await loading_message.edit(embed=embed_updated)

    else:
        print("Le canal spécifié n'est pas un ForumChannel.")
        if ctx:
            await ctx.send("Le canal spécifié n'est pas un ForumChannel.")


# Scheduler pour exécuter la fonction send_joblist deux fois par jour
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=8, minute=0)  # Exécuter à 8h du matin
async def joblist_morning():
    await send_joblist()
    print(f"Updated jobs list auto 1!")


@scheduler.scheduled_job("cron", hour=14, minute=10)  # Exécuter à 16h
async def joblist_evening():
    await send_joblist()
    print(f"Updated jobs list auto 2!")


@bot.command(name='update_jobs')
async def update_jobs(ctx):
    """Force la mise à jour des offres d'emploi."""
    # await ctx.send(f"Updated jobs list !")
    embed_loading = discord.Embed(
        title="Mise à jour en cours",
        description="La liste des offres d'emploi est en cours de mise à jour, veuillez patienter...",
        color=discord.Color.orange()
    )
    embed_loading.set_thumbnail(
        url="https://i.imgur.com/5AGlfwy.gif")  # Lien vers une icône d'engrenage animée
    loading_message = await ctx.send(embed=embed_loading)

    await send_joblist(ctx, loading_message)
    # await ctx.send(f"Fini !")


@bot.command()
async def ping(ctx):
    """Renvoie la latence du bot en millisecondes."""
    await ctx.send(f"Pong! {round(bot.latency * 1000)}ms")


@bot.event
async def on_ready():
    print('Bot is ready.')
    # Démarrage du scheduler pour exécuter la fonction send_joblist deux fois par jour
    scheduler.start()


# HELP COMMAND

attributes = {
    'name': "help",
    'aliases': ["helpme"],
    'cooldown': commands.CooldownMapping.from_cooldown(3, 5, commands.BucketType.user),
}


class SupremeHelpCommand(commands.HelpCommand):
    def get_command_signature(self, command):
        return '%s%s %s' % (self.context.clean_prefix, command.qualified_name, command.signature)

    async def send_bot_help(self, mapping):
        embed = discord.Embed(title="Help", color=discord.Color.blurple())
        for cog, commands in mapping.items():
            filtered = await self.filter_commands(commands, sort=True)
            if command_signatures := [
                self.get_command_signature(c) for c in filtered
            ]:
                cog_name = getattr(cog, "qualified_name", "No Category")
                embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_command_help(self, command):
        embed = discord.Embed(title=self.get_command_signature(command), color=discord.Color.blurple())
        if command.help:
            embed.description = command.help
        if alias := command.aliases:
            embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

        channel = self.get_destination()
        await channel.send(embed=embed)

    async def send_help_embed(self, title, description, commands):  # a helper function to add commands to an embed
        embed = discord.Embed(title=title, description=description or "No help found...")

        if filtered_commands := await self.filter_commands(commands):
            for command in filtered_commands:
                embed.add_field(name=self.get_command_signature(command), value=command.help or "No help found...")

        await self.get_destination().send(embed=embed)

    async def send_group_help(self, group):
        title = self.get_command_signature(group)
        await self.send_help_embed(title, group.help, group.commands)

    async def send_cog_help(self, cog):
        title = cog.qualified_name or "No"
        await self.send_help_embed(f'{title} Category', cog.description, cog.get_commands())

    async def send_error_message(self, error):
        embed = discord.Embed(title="Error", description=error, color=discord.Color.red())
        channel = self.get_destination()

        await channel.send(embed=embed)


bot.help_command = SupremeHelpCommand(command_attrs=attributes)

token = os.getenv('TOKEN')
bot.run(token)
