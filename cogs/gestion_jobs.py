import re
import discord
from discord.ext import commands
import asyncio

from utils.config_loader import forum_channel_id, role_ping
from utils.get_details_indeed import get_details_indeed
from utils.job_fetcher import fetch_linkedin_jobs, fetch_indeed_jobs, fetch_new_jobs


class JobCog(commands.Cog):
    """Cog pour la gestion des offres d'emploi."""

    def __init__(self, bot):
        self.bot = bot

    async def send_joblist(self, ctx=None, loading_message=None):
        global bugs

        forum_channel = ctx.guild.get_channel(forum_channel_id)

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
                link = job.get("linkedin_job_url_cleaned")
                technologies = job.get('skills', 'Non spécifié')
                city = job.get('job_location', 'Non spécifié') or job.get('location', 'Non spécifié')
                indeed_link = job.get("link")


                if indeed_link and not link:
                    if isinstance(indeed_link, str):  # Check if indeed_link is a string
                        match = re.search(r'/job/([^/?]+)', indeed_link)  # Changed to indeed_link
                        if match:
                            indeed_id = match.group(1)
                            # Get the details using the ID
                            indeed_details = get_details_indeed(indeed_id)

                            # Extract the indeed_final_url from the details
                            if indeed_details:
                                link = indeed_details.get("indeed_final_url")  # Adjust if it's an object
                            else:
                                print("No details found for this job.")
                        else:
                            print("No valid Indeed ID found in the link.")
                    else:
                        print("Indeed link is not a valid string.")
                else:
                    print("No Indeed link provided for the job.")

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
            if loading_message:
                embed_updated = discord.Embed(
                    title="Erreur lors de la mise à jour",
                    description="Le canal spécifié n'est pas un ForumChannel.",
                    color=discord.Color.red()
                )
                await loading_message.edit(embed=embed_updated)

    @commands.command(name='update_jobs')
    async def update_jobs(self, ctx):
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

        await self.send_joblist(ctx, loading_message)
        # await ctx.send(f"Fini !")


async def setup(bot):
    await bot.add_cog(JobCog(bot))
