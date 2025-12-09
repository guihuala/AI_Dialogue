public class MsgConst
{
    // Save System Events (Range 1000-1100)
    public const int MSG_SAVE_LOADING_START = 1001;
    public const int MSG_SAVE_LOADING_END = 1002;
    public const int MSG_SAVE_MESSAGE_SHOW = 1003; // Params: string message
    public const int MSG_SAVE_SLOT_CLICKED = 1004; // Params: string slotId

    // Game UI Events (Range 2000-2100)
    public const int MSG_GAME_UPDATE_STATS = 2001; // Params: float money, float sanity, float gpa, int day, string time
    public const int MSG_GAME_BUBBLE_CREATE = 2002;
    public const int MSG_GAME_BUBBLE_UPDATE = 2003; // Params: string content
    public const int MSG_GAME_BUBBLE_DESTROY = 2004;
    public const int MSG_GAME_ADD_MESSAGE = 2005; // Params: string name, string content
    public const int MSG_GAME_SHOW_OPTIONS = 2006; // Params: List<StoryOption>
    public const int MSG_GAME_CLEAR_OPTIONS = 2007;
    public const int MSG_GAME_OPTION_CLICKED = 2008; // Params: StoryOption
}