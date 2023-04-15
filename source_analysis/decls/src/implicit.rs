use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize, Debug, Clone)]
pub enum FnType {
    Safe,
    Unsafe,
    NormalNotSafe,
    Parametric,
}

#[derive(Serialize, Deserialize, Debug, Clone)]
pub struct UnsafeInBody {
    pub file: String,
    pub line: String,
    pub def_path: String,
    pub fn_type: FnType,
    pub name: String,
}

impl UnsafeInBody {
    pub fn new(file: String, line: String, def_path: String, fn_type: FnType, name: String ) -> Self {
        UnsafeInBody {
            file,
            line,
            def_path,
            fn_type,
            name,
        }
    }
}