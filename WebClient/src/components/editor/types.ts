export type Category = 'world' | 'scene' | 'char' | 'event' | 'skills' | 'relation' | 'all';

export interface EditorFile {
    type: 'md' | 'csv';
    name: string;
}
