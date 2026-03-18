export type Category = 'world' | 'char' | 'event' | 'skills' | 'all';

export interface EditorFile {
    type: 'md' | 'csv';
    name: string;
}
