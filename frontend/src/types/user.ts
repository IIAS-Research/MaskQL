import { BaseResource } from "./base";

export interface User {
    id: number;
    username: string;
    password: string;
}

export type UserCreate = Omit<User, "id">;
export type UserUpdate = Partial<Omit<User, "id">>;

export class Users extends BaseResource<User, UserCreate, UserUpdate> {
    constructor() {
        super("/users");
    }
}

export const UserAPI = new Users();
