from discord import app_commands, Interaction

class TailorResume:
    def __init__(self, tree: app_commands.CommandTree):
        if not tree:
            raise ValueError("No tree available, discord bot failed to run")
        self.tree = tree  
        self._register()
    
    def _register(self):
        @self.tree.command(name="tailor_resume", description="tailors resume for user")
        async def tailor_resume(interaction: Interaction):
            await interaction.response.send_message("Not yet implemented")