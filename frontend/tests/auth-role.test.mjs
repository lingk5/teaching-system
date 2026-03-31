import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';


const authFile = path.resolve('frontend/src/js/auth.js');
const authSource = fs.readFileSync(authFile, 'utf8');


function createElement(capability = '') {
    return {
        dataset: capability ? { capability } : {},
        style: { display: '' },
        textContent: '',
    };
}


function loadAuthContext({ role = 'teacher', selectorMap = {}, elementMap = {} } = {}) {
    const store = new Map([
        ['token', 'test-token'],
        ['userInfo', JSON.stringify({ role, name: '测试用户' })],
    ]);

    const context = {
        console,
        alert: () => {},
        localStorage: {
            getItem(key) {
                return store.has(key) ? store.get(key) : null;
            },
            setItem(key, value) {
                store.set(key, value);
            },
            removeItem(key) {
                store.delete(key);
            },
            clear() {
                store.clear();
            },
        },
        document: {
            getElementById(id) {
                return elementMap[id] || null;
            },
            querySelectorAll(selector) {
                return selectorMap[selector] || [];
            },
        },
        window: {
            location: {
                pathname: '/pages/dashboard.html',
                href: '',
            },
            currentUser: {},
        },
        Set,
        URLSearchParams,
    };

    context.window.document = context.document;
    context.window.localStorage = context.localStorage;

    vm.runInNewContext(authSource, context, { filename: authFile });
    return context;
}


test('currentUserCan exposes role capabilities', () => {
    const adminContext = loadAuthContext({ role: 'admin' });
    assert.equal(typeof adminContext.currentUserCan, 'function');
    assert.equal(adminContext.currentUserCan('manage_users'), true);
    assert.equal(adminContext.currentUserCan('manage_courses'), true);

    const teacherContext = loadAuthContext({ role: 'teacher' });
    assert.equal(teacherContext.currentUserCan('manage_users'), false);
    assert.equal(teacherContext.currentUserCan('manage_courses'), true);

    const assistantContext = loadAuthContext({ role: 'assistant' });
    assert.equal(assistantContext.currentUserCan('manage_courses'), false);
    assert.equal(assistantContext.currentUserCan('process_warnings'), false);
});


test('applyRoleUI hides capability-gated controls for unauthorized roles', () => {
    const manageUsersControl = createElement('manage_users');
    const manageCoursesControl = createElement('manage_courses');
    const userRoleLabel = createElement();

    const context = loadAuthContext({
        role: 'teacher',
        selectorMap: {
            '[data-capability]': [manageUsersControl, manageCoursesControl],
        },
        elementMap: {
            userRole: userRoleLabel,
        },
    });

    context.applyRoleUI();

    assert.equal(manageUsersControl.style.display, 'none');
    assert.notEqual(manageCoursesControl.style.display, 'none');
    assert.equal(userRoleLabel.textContent, '教师');
});
