import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';


const dashboardFile = path.resolve('frontend/src/pages/dashboard.html');
const analyticsFile = path.resolve('frontend/src/pages/analytics.html');


test('dashboard page removes mock fallback data and uses empty states', () => {
    const source = fs.readFileSync(dashboardFile, 'utf8');

    assert.equal(source.includes('const MOCK ='), false);
    assert.equal(source.includes('模拟数据兜底'), false);
    assert.equal(source.includes('attendanceRate: \'85%\''), false);
    assert.equal(source.includes('暂无数据'), true);
});


test('analytics page removes demo ranking fallback and mock charts', () => {
    const source = fs.readFileSync(analyticsFile, 'utf8');

    assert.equal(source.includes('const MOCK_DATA ='), false);
    assert.equal(source.includes('当前显示演示数据'), false);
    assert.equal(source.includes('grade_profile'), false);
    assert.equal(source.includes('暂无数据'), true);
});
