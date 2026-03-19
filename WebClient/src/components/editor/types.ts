export type Category = 'world' | 'char' | 'event' | 'skills' | 'relation' | 'all';

export interface EditorFile {
    type: 'md' | 'csv';
    name: string;
}
