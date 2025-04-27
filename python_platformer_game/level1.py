"""
Platformer Game
"""
import arcade
import arcade.gui

# Constants
SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 650
COINS_COLLECTED = 11
SCREEN_TITLE = "Platform"
CHARACTER_SCALING = 1.5
TILE_SCALING = 1.5
COIN_SCALING = 0.5
MOVEMENT_SPEED = 5
PLAYER_MOVEMENT_SPEED = 5
GRAVITY = 0.5
PLAYER_JUMP_SPEED = 8

# Player coordinate constants
PLAYER_START_X = 241
PLAYER_START_Y = 96
PLAYER_START_Y_THREE = 693
PLAYER_TP_X = 267.75
PLAYER_TP_Y = 688.25
PLAYER_TP_X_BACK = 362
PLAYER_TP_Y_BACK = 30.25

RIGHTFACING = 0
LEFTFACING = 1

# Layer names
LAYER_NAME_PLATORMS = "Platforms"
LAYER_NAME_COINS = "Coins"
LAYER_NAME_BACKGROUND = "Background"
LAYER_NAME_DONT_TOUCH = "Don't Touch"
LAYER_NAME_ENEMIES = "Enemies"
LAYER_NAME_MOVING_PLATFORM = "Moving Platform"
LAYER_NAME_LADDERS = "Ladders"
LAYER_NAME_TELEPORTER = "Teleport"
LAYER_NAME_TELEPORTER_BACK = "Teleport Back"
LAYER_NAME_PLAYER = "Player"

# global variables
total_time_display = 0
total_death_display = 0


def load_texture_pair(filename):
    '''
    Function to load a pair of mirror images for character animations
    '''
    return [
        arcade.load_texture(filename),
        arcade.load_texture(filename, flipped_horizontally=True),
    ]


class PlayerCharacter(arcade.Sprite):
    '''
    Class for animations used for player character
    '''
    def __init__(self):

        super().__init__()

        # Default to facing right
        self.character_facedirection = RIGHTFACING

        # Used for image sequences
        self.cur_texture = 0
        self.scale = CHARACTER_SCALING

        self.jumping = False
        self.climbing = False
        self.is_on_ladder = False
        main_path = ("animations/tile")

        self.idle_texture_pair = load_texture_pair(f"{main_path}_0139.png")
        self.jump_texture_pair = load_texture_pair(f"{main_path}_jump.png")
        self.fall_texture_pair = load_texture_pair(f"{main_path}_fall.png")

        # Load character walking textures
        self.walk_textures = []
        for i in range(3):
            texture = load_texture_pair(f"{main_path}_walk{i}.png")
            self.walk_textures.append(texture)

        # Load character climbing textures
        self.climbing_textures = []
        texture = arcade.load_texture(f"{main_path}_climb0.png")
        self.climbing_textures.append(texture)
        texture = arcade.load_texture(f"{main_path}_climb1.png")
        self.climbing_textures.append(texture)

        # Setting the texture when the character is idle
        self.texture = self.idle_texture_pair[0]

    def update_animation(self, delta_time: float = 1 / 60):
        """
        Function used to change textures when the player should be animated
        """
        # Changing if the character should face left or right
        if self.change_x < 0 and self.character_facedirection == RIGHTFACING:
            self.character_facedirection = LEFTFACING
        elif self.change_x > 0 and self.character_facedirection == LEFTFACING:
            self.character_facedirection = RIGHTFACING

        # Player animations when they are climbing the ladder
        if self.is_on_ladder:
            self.climbing = True
        if not self.is_on_ladder and self.climbing:
            self.climbing = False
        if self.climbing and abs(self.change_y) > 1:
            self.cur_texture += 1
            if self.cur_texture > 7:
                self.cur_texture = 0
        if self.climbing:
            self.texture = self.climbing_textures[self.cur_texture // 4]
            return

        # Player animation for jumping
        if self.change_y > 0 and not self.is_on_ladder:
            self.texture = self.jump_texture_pair[self.character_facedirection]
            return
        elif self.change_y < 0 and not self.is_on_ladder:
            self.texture = self.fall_texture_pair[self.character_facedirection]
            return

        # When the player is idle
        if self.change_x == 0:
            self.texture = self.idle_texture_pair[self.character_facedirection]
            return

        # Player animation for walking
        self.cur_texture += 1
        if self.cur_texture > 2:
            self.cur_texture = 0
        self.texture = self.walk_textures[self.cur_texture][
            self.character_facedirection
        ]


class MainMenu(arcade.View):
    """
    Class used to display main menu 
    """

    def __init__(self):
        """
        This is run once when we switch to this view
        """
        super().__init__()

        # Setting the backgroud for instruction screen
        self.texture = arcade.load_texture("Backgrounds/instructions.png")

        # UI Manager to handle the UI for the instruction screen
        self.uimanager = arcade.gui.UIManager()
        self.uimanager.enable()

        # Creating the continue button
        start_button = arcade.gui.UIFlatButton(text="Continue", width=200)
        start_button.on_click = self.on_buttonclick
        self.uimanager.add(arcade.gui.UIAnchorWidget(anchor_x="center_x",
                           anchor_y="center_y", child=start_button))

    def on_buttonclick(self, event):
        """
        Use a mouse press to advance to the 'game' view.
        """
        game_view = GameView()
        self.window.show_view(game_view)

    def on_draw(self):
        """
        Draw this view
        """
        arcade.start_render()
        self.texture.draw_sized(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2,
                                SCREEN_WIDTH, SCREEN_HEIGHT)
        self.uimanager.draw()


class GameView(arcade.View):
    """
    Main application class.
    """

    def __init__(self):

        # Initializer for the game
        super().__init__()

        # arcade.set_background_color(arcade.csscolor.DEEP_SKY_BLUE)

        # To keep track of time on each level
        self.total_time = 0.0
        self.output = "00:00:00"
        self.time_level1 = 0
        self.time_level2 = 0
        self.time_level3 = 0

        self.background = None

        # Track the current state of what key is pressed
        self.left_pressed = False
        self.right_pressed = False
        self.up_pressed = False
        self.down_pressed = False
        self.jump_needs_reset = False

        # Our Scene Object
        self.scene = None

        # Our TileMap Object
        self.tile_map = None

        # Keep track of sprite lists
        self.coin_list = None
        self.wall_list = None
        self.enemies_list = None
        self.moving_wall_list = None

        # Separate variable that holds the player sprite
        self.player_sprite = None
        self.player_list = None
        # Our 'physics' engine
        self.physics_engine = None
        # A Camera that can be used for scrolling the screen
        self.camera = None

        # Load sounds
        self.collect_coin_sound = arcade.load_sound(":resources:sounds/"
                                                    "coin1.wav")
        self.jump_sound = arcade.load_sound(":resources:sounds/jump1.wav")
        self.game_over = arcade.load_sound(":resources:sounds/gameover1.wav")
        self.teleport_sound = arcade.load_sound(":resources:sounds/"
                                                "phaseJump1.wav")

        # A Camera that can be used to draw GUI elements
        self.gui_camera = None

        # Keep track of the score, death and level
        self.score = 0
        self.death = 0
        self.level = 1

        # Setting up a different starting height for different levels
        self.start_y = PLAYER_START_Y

    def setup(self):
        """
        Set up the game here. Call this function to restart the game.
        """

        # Set up the Cameras
        self.gui_camera = arcade.Camera(self.window.width, self.window.height)
        self.camera = arcade.Camera(self.window.width, self.window.height)

        # Setting background image
        self.background = arcade.load_texture("Backgrounds/"
                                              "backgrounds.png")

        # Finding the map for each level
        map_path = ("")
        map_name = (f"{map_path}map1_level_{self.level}.tmx")
        layer_options = {
            "Platforms": {
                "use_spatial_hash": True,
            },
        }

        # Layer Specific Options for the Tilemap
        layer_options = {
            LAYER_NAME_PLATORMS: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_COINS: {
                "use_spatial_hash": True,
            },
            LAYER_NAME_DONT_TOUCH: {
                "use_spatial_hash": True,
            },

            LAYER_NAME_ENEMIES: {
                "use_spatial_hash": False,
            },

            LAYER_NAME_MOVING_PLATFORM: {
                "use_spatial_hash": False,
            },

            LAYER_NAME_TELEPORTER: {
                "use_spatial_hash": True,
            },

            LAYER_NAME_TELEPORTER_BACK: {
                "use_spatial_hash": True,
            },

            LAYER_NAME_LADDERS: {
                "use_spatial_hash": True,
            },
        }

        # Load in TileMap
        self.tile_map = arcade.load_tilemap(map_name,
                                            TILE_SCALING, layer_options)

        # Initiate New Scene with our TileMap,
        # this will automatically add all layers
        # from the map as SpriteLists in the scene in the proper order.
        self.scene = arcade.Scene.from_tilemap(self.tile_map)

        # Keep track of the score in the level
        self.score = 0

        # self.scene.add_sprite_list_before("Player",
        #                                   LAYER_NAME_FOREGROUND)
        # self.scene = arcade.Scene()

        # Keep track of time of level
        self.displaytotaltime = 0
        self.total_time = 0.0

        # If the level is on 3 then the player should start higher up
        if self.level == 3:
            self.start_y = PLAYER_START_Y_THREE

        # Set up the player, specifically
        # placing it at these coordinates.
        self.player_sprite = PlayerCharacter()
        self.player_sprite.center_x = PLAYER_START_X
        self.player_sprite.center_y = self.start_y
        self.scene.add_sprite(LAYER_NAME_PLAYER, self.player_sprite)
        self.scene.add_sprite_list("walls", use_spatial_hash=True)

        # image_source = ("C:/Users/nanda/OneDrive - Westlake Boys High School"
        # "/13 - DTP/assessment/python assessment_final/Tiles/tile_0139.png")
        # self.player_sprite = arcade.Sprite(image_source, CHARACTER_SCALING)
        # self.player_sprite.center_x = PLAYER_START_X
        # self.player_sprite.center_y = PLAYER_START_Y
        # self.scene.add_sprite("Player", self.player_sprite)

        if self.tile_map.background_color:
            arcade.set_background_color(self.tile_map.background_color)

        self.physics_engine = arcade.PhysicsEnginePlatformer(
            self.player_sprite,
            platforms=self.scene[LAYER_NAME_MOVING_PLATFORM],
            gravity_constant=GRAVITY,
            ladders=self.scene[LAYER_NAME_LADDERS],
            walls=self.scene["Platforms"]
        )
        self.physics_engine.platforms.append(self.scene[LAYER_NAME_ENEMIES])

    def on_show(self):
        self.setup()

    def on_draw(self):
        """
        Render the screen.
        """

        # Clear the background screen
        self.clear()

        # If the player is on level 3 and goes to a lower part,
        # it changes the background to a cave
        if self.level == 3 and self.player_sprite.center_y < 409:
            self.background = arcade.load_texture("Backgrounds/cave.png")

        arcade.draw_lrwh_rectangle_textured(0, 0, SCREEN_WIDTH,
                                            SCREEN_HEIGHT, self.background)

        # Activate the game camera
        self.camera.use()

        # Draw the Scene
        self.scene.draw()

        # Activate the GUI camera before drawing GUI elements
        self.gui_camera.use()

        # Drawing the score, death count and timer as well as the
        # shadow on each and being able to follow the character
        score_text = f"Score: {self.score}"
        time_text = f"Time: {self.output}"
        death_text = f"Deaths: {self.death}"
        arcade.draw_text(
            score_text,
            10,
            10,
            arcade.csscolor.BLACK,
            18,
            font_name="Kenney Pixel Square"
        )

        arcade.draw_text(
            score_text,
            13,
            13,
            arcade.csscolor.WHITE,
            18,
            font_name="Kenney Pixel Square"
        )

        arcade.draw_text(
            death_text,
            10,
            40,
            arcade.csscolor.BLACK,
            18,
            font_name="Kenney Pixel Square"
        )

        arcade.draw_text(
            death_text,
            13,
            43,
            arcade.csscolor.WHITE,
            18,
            font_name="Kenney Pixel Square"
        )

        arcade.draw_text(
            time_text,
            10,
            70,
            arcade.csscolor.BLACK,
            18,
            font_name="Kenney Pixel Square"
        )

        arcade.draw_text(
            time_text,
            13,
            73,
            arcade.csscolor.WHITE,
            18,
            font_name="Kenney Pixel Square"
        )

    def process_keychange(self):
        """
        Called when we change a key up/down or we move on/off a ladder.
        """
        # Process up/down
        if self.up_pressed and not self.down_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = PLAYER_MOVEMENT_SPEED
            elif (
                self.physics_engine.can_jump(y_distance=10) and not
                self.jump_needs_reset
            ):
                self.player_sprite.change_y = PLAYER_JUMP_SPEED
                self.jump_needs_reset = True
                arcade.play_sound(self.jump_sound)
        elif self.down_pressed and not self.up_pressed:
            if self.physics_engine.is_on_ladder():
                self.player_sprite.change_y = -PLAYER_MOVEMENT_SPEED

        # Process up/down when on a ladder and no movement
        if self.physics_engine.is_on_ladder():
            if not self.up_pressed and not self.down_pressed:
                self.player_sprite.change_y = 0
            elif self.up_pressed and self.down_pressed:
                self.player_sprite.change_y = 0

        # Process left/right
        if self.right_pressed and not self.left_pressed:
            self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED
        elif self.left_pressed and not self.right_pressed:
            self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        else:
            self.player_sprite.change_x = 0

    def on_key_press(self, key, modifiers):
        """
        Called whenever a key is pressed.
        """
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = True
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = True
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = True
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = True

        self.process_keychange()
        # if key == arcade.key.UP or key == arcade.key.W:
        #     if self.physics_engine.can_jump():
        #         self.player_sprite.change_y = PLAYER_JUMP_SPEED
        #         arcade.play_sound(self.jump_sound)
        # elif key == arcade.key.LEFT or key == arcade.key.A:
        #     self.player_sprite.change_x = -PLAYER_MOVEMENT_SPEED
        # elif key == arcade.key.RIGHT or key == arcade.key.D:
        #     self.player_sprite.change_x = PLAYER_MOVEMENT_SPEED

    def on_key_release(self, key, modifiers):
        """Called when the user releases a key."""
        if key == arcade.key.UP or key == arcade.key.W:
            self.up_pressed = False
            self.jump_needs_reset = False
        elif key == arcade.key.DOWN or key == arcade.key.S:
            self.down_pressed = False
        elif key == arcade.key.LEFT or key == arcade.key.A:
            self.left_pressed = False
        elif key == arcade.key.RIGHT or key == arcade.key.D:
            self.right_pressed = False

        self.process_keychange()
        # if key == arcade.key.UP or key == arcade.key.W:
        #     self.up_pressed = False
        #     self.jump_needs_reset = False
        # elif key == arcade.key.LEFT or key == arcade.key.A:
        #     self.player_sprite.change_x = 0
        # elif key == arcade.key.RIGHT or key == arcade.key.D:
        #     self.player_sprite.change_x = 0

    def center_camera_to_player(self):
        screen_center_x = (self.player_sprite.center_x -
                           (self.camera.viewport_width / 2))
        screen_center_y = (self.player_sprite.center_y -
                           (self.camera.viewport_height / 2))

        if screen_center_x < 0:
            screen_center_x = 0
        if screen_center_y < 0:
            screen_center_y = 0
        player_centered = (screen_center_x, screen_center_y)
        self.camera.move_to(player_centered)

    def on_update(self, delta_time):
        """
        Movement and game logic
        """

        # Move the player with the physics engine
        self.physics_engine.update()

        # Update global variables
        global total_time_display
        global total_death_display

        # Update animations
        if self.physics_engine.can_jump():
            self.player_sprite.can_jump = False
        else:
            self.player_sprite.can_jump = True

        if (self.physics_engine.is_on_ladder() and not
           self.physics_engine.can_jump()):
            self.player_sprite.is_on_ladder = True
            self.process_keychange()
        else:
            self.player_sprite.is_on_ladder = False
            self.process_keychange()

        # Update Animations
        self.scene.update_animation(
            delta_time, [LAYER_NAME_COINS, LAYER_NAME_BACKGROUND,
                         LAYER_NAME_PLAYER]
        )

        # Checking if player hits coins so it can collect it
        coin_hit_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Coins"]
        )
        for coin in coin_hit_list:
            coin.remove_from_sprite_lists()
            arcade.play_sound(self.collect_coin_sound)
            self.score += 1

        # Position the camera
        self.center_camera_to_player()
        self.scene.update([LAYER_NAME_MOVING_PLATFORM, LAYER_NAME_ENEMIES])

        # Checking if player hits an enemy or "don't touch" to
        # reset the level
        dont_touch_hit_list = arcade.check_for_collision_with_lists(
            self.player_sprite, [self.scene["Don't Touch"],
                                 self.scene["Enemies"], ],
        )
        for hit in dont_touch_hit_list:
            arcade.play_sound(self.game_over)
            self.death += 1
            total_death_display = self.death
            # game_over = GameOverView()
            # self.window.show_view(game_over)
            self.setup()
            return

        # Checking if player touches a teleporter
        # to be teleported to the other door
        teleport_touch_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Teleport"]
        )
        for tp in teleport_touch_list:
            arcade.play_sound(self.teleport_sound)
            self.player_sprite.center_x = PLAYER_TP_X
            self.player_sprite.center_y = PLAYER_TP_Y

        teleport_back_touch_list = arcade.check_for_collision_with_list(
            self.player_sprite, self.scene["Teleport Back"]
        )
        for tp in teleport_back_touch_list:
            arcade.play_sound(self.teleport_sound)
            self.player_sprite.center_x = PLAYER_TP_X_BACK
            self.player_sprite.center_y = PLAYER_TP_Y_BACK

        # if self.level == 3 and self.score == COINS_COLLECTED:
        #     self.displaytotaltime= (self.time_level1 +
        #                             self.time_level2 +
        #                             self.time_level3)
        #
        #     tot = self.displaytotaltime
        #     game_complete = GameCompleteView()
        #    self.window.show_view(game_complete)
        #     return

        # Checking if the player collects all the coins
        # to go to the next level
        if self.score == COINS_COLLECTED:
            # Saving the time the player collects all the coins
            # so they can be added as a total time when the
            # player finishes the game
            if self.level == 1:
                self.time_level1 = self.total_time
            elif self.level == 2:
                self.time_level2 = self.total_time
            elif self.level == 3:
                self.time_level3 = self.total_time
                self.displaytotaltime = (self.time_level1 +
                                         self.time_level2 + self.time_level3)
                total_time_display = self.displaytotaltime
                game_complete = GameCompleteView()
                self.window.show_view(game_complete)
                return
            self.level += 1
            self.setup()
            return

        #  Calculating time
        self.total_time += delta_time

        # Calculate minutes
        minutes = int(self.total_time) // 60

        # Calculate seconds by using a modulus (remainder)
        seconds = int(self.total_time) % 60

        # Calculate 100s of a second
        seconds_100s = int((self.total_time - seconds) * 100)

        # Figure out our output
        self.output = f"{minutes:02d}:{seconds:02d}:{seconds_100s:02d}"

'''class GameOverView(arcade.View):
    """
    Class to manage the game overview
    """

    def on_show(self):
        """
        Called when switching to this view
        """
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        """
        Draw the game overview
        """
        self.clear()
        arcade.draw_text(
            "Game Over - Click to restart",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2,
            arcade.color.RED,
            30,
            font_name = "Kenney Pixel Square",
            anchor_x="center",
        )

    def on_mouse_press(self, _x, _y, _button, _modifiers):
        """
        Use a mouse press to advance to the 'game' view.
        """
        game_view = GameView()
        game_view.setup()
        self.window.show_view(game_view)'''


class GameCompleteView(arcade.View):
    '''
    Goes to this screen when the user finishes the game
    and displays their death count and total time
    '''
    def on_show(self):
        """
        Called when switching to this view
        """
        arcade.set_background_color(arcade.color.BLACK)

    def on_draw(self):
        """
        Draw the game overview
        """
        self.clear()
        global total_time_display
        global total_death_display
        arcade.draw_text(
            "Congratulations!!!",
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 1.5,
            arcade.color.WHITE,
            30,
            font_name="Kenney Pixel Square",
            anchor_x="center",
        )

        arcade.draw_text(
            ("You finished the game with a time of " +
             str(round(total_time_display, 2)) +
             " and a death count of " + str(total_death_display)),
            SCREEN_WIDTH / 2,
            SCREEN_HEIGHT / 2,
            arcade.color.WHITE,
            20,
            font_name="Kenney Pixel Square",
            anchor_x="center",
            multiline=True,
            width=600
        )


def main():
    """
    Main function
    """
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
    menu_view = MainMenu()
    window.show_view(menu_view)
    arcade.run()


if __name__ == "__main__":
    main()
